package scheduler

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/humumu/journal-monitor/internal/cache"
	"github.com/humumu/journal-monitor/internal/config"
	"github.com/humumu/journal-monitor/internal/fetcher"
	"github.com/humumu/journal-monitor/internal/matcher"
	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/notifier"
	"github.com/humumu/journal-monitor/internal/repo"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

type Scheduler struct {
	journals   *repo.JournalRepo
	articles   *repo.ArticleRepo
	subRepo    *repo.SubscriptionRepo
	userRepo   *repo.UserRepo
	notifRepo  *repo.NotificationRepo
	dedupCache *cache.DedupCache
	fetcherMgr *fetcher.Manager
	matcher    *matcher.Engine
	emailNtfr  *notifier.EmailNotifier
	wechatNtfr *notifier.WeChatNotifier
	pool       *pgxpool.Pool
	interval   time.Duration
	stopCh     chan struct{}
	wg         sync.WaitGroup
}

func New(
	pool *pgxpool.Pool,
	rdb *redis.Client,
	cfg *config.Config,
	journals *repo.JournalRepo,
	articles *repo.ArticleRepo,
	subRepo *repo.SubscriptionRepo,
	userRepo *repo.UserRepo,
	notifRepo *repo.NotificationRepo,
) *Scheduler {
	return &Scheduler{
		journals:   journals,
		articles:   articles,
		subRepo:    subRepo,
		userRepo:   userRepo,
		notifRepo:  notifRepo,
		dedupCache: cache.NewDedupCache(rdb),
		fetcherMgr: fetcher.NewManager(),
		matcher:    matcher.NewEngine(subRepo, userRepo),
		emailNtfr:  notifier.NewEmailNotifier(cfg.SMTP),
		wechatNtfr: notifier.NewWeChatNotifier(cfg.WeChat),
		pool:       pool,
		interval:   cfg.Fetch.DefaultInterval,
		stopCh:     make(chan struct{}),
	}
}

func (s *Scheduler) Start(ctx context.Context) {
	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		ticker := time.NewTicker(s.interval)
		defer ticker.Stop()

		s.fetchAndNotify(ctx)

		for {
			select {
			case <-ticker.C:
				s.fetchAndNotify(ctx)
			case <-s.stopCh:
				log.Println("scheduler stopped")
				return
			case <-ctx.Done():
				return
			}
		}
	}()
	s.startDailySummary(ctx)
	log.Printf("scheduler started with interval %v", s.interval)
}

func (s *Scheduler) Stop() {
	close(s.stopCh)
	s.wg.Wait()
}

func (s *Scheduler) fetchAndNotify(ctx context.Context) {
	log.Println("scheduler: starting fetch cycle")

	journals, err := s.journals.GetAllActive(ctx)
	if err != nil {
		log.Printf("scheduler: failed to get active journals: %v", err)
		return
	}

	if len(journals) == 0 {
		log.Println("scheduler: no active journals to fetch")
		return
	}

	results := s.fetcherMgr.FetchAll(ctx, journals)

	for _, result := range results {
		if result.Err != nil {
			log.Printf("scheduler: fetch failed [%s]: %v", result.JournalName, result.Err)
			continue
		}
		log.Printf("scheduler: fetched %d articles from %s (took %v)",
			len(result.Articles), result.JournalName, result.Duration)

		for _, raw := range result.Articles {
			s.processArticle(ctx, result.JournalID, raw)
		}
	}

	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		s.sendPendingNotifications(ctx)
	}()
}

func (s *Scheduler) processArticle(ctx context.Context, journalID string, raw fetcher.RawArticle) {
	isDup, err := s.dedupCache.IsDuplicate(ctx, journalID, raw.DOI)
	if err != nil {
		log.Printf("scheduler: dedup error [%s/%s]: %v", journalID, raw.DOI, err)
		return
	}
	if raw.DOI == "" {
		// Fall back to URL-based dedup for sources without DOIs (e.g., CNKI)
		var urlErr error
		isDup, urlErr = s.dedupCache.IsDuplicateByURL(ctx, journalID, raw.URL)
		if urlErr != nil {
			log.Printf("scheduler: dedup url error [%s/%s]: %v", journalID, raw.URL, urlErr)
			return
		}
	}
	if isDup {
		return
	}

	var publishDate *time.Time
	if raw.PublishDate != "" {
		t, err := time.Parse("2006-01-02", raw.PublishDate)
		if err == nil {
			publishDate = &t
		}
	}

	article := &model.Article{
		DOI:         raw.DOI,
		Title:       raw.Title,
		Authors:     raw.Authors,
		Abstract:    raw.Abstract,
		JournalID:   journalID,
		PublishDate: publishDate,
		URL:         raw.URL,
	}
	if article.Authors == nil {
		article.Authors = []string{}
	}
	if article.Abstract == "" && raw.Abstract != "" {
		// Try to extract abstract from RSS description (arXiv format: "arXiv:... Announce Type: ... \nAbstract: ...")
		parts := strings.Split(raw.Abstract, "Abstract:")
		if len(parts) > 1 {
			article.Abstract = strings.TrimSpace(parts[len(parts)-1])
		}
	}
	if err := s.articles.Create(ctx, article); err != nil {
		log.Printf("scheduler: save article error [%s]: %v", raw.DOI, err)
		return
	}

	matches := s.matcher.Match(ctx, article)

	for _, m := range matches {
		notif := &model.Notification{
			UserID:    m.UserID,
			ArticleID: article.ID,
			Channel:   m.Channel,
			Status:    "pending",
		}
		if err := s.notifRepo.Create(ctx, notif); err != nil {
			log.Printf("scheduler: create notification error: %v", err)
		}
	}
}

func (s *Scheduler) sendPendingNotifications(ctx context.Context) {
	notifs, err := s.notifRepo.GetPending(ctx)
	if err != nil {
		log.Printf("scheduler: get pending notifications error: %v", err)
		return
	}

	for _, n := range notifs {
		article, err := s.notifRepo.GetArticleWithJournal(ctx, n.ArticleID)
		if err != nil {
			log.Printf("scheduler: get article error: %v", err)
			s.notifRepo.MarkFailed(ctx, n.ID, "article not found")
			continue
		}

		user, err := s.userRepo.GetByID(ctx, n.UserID)
		if err != nil || user == nil {
			log.Printf("scheduler: get user error: %v", err)
			s.notifRepo.MarkFailed(ctx, n.ID, "user not found")
			continue
		}

		var sendErr error
		switch n.Channel {
		case "email":
			sendErr = s.emailNtfr.Send(ctx, user, article)
		case "wechat":
			sendErr = s.wechatNtfr.Send(ctx, user, article)
		default:
			sendErr = fmt.Errorf("unknown channel: %s", n.Channel)
		}

		if sendErr != nil {
			log.Printf("scheduler: send notification error [%s/%s]: %v",
				n.Channel, n.ID, sendErr)
			s.notifRepo.MarkFailed(ctx, n.ID, sendErr.Error())
		} else {
			s.notifRepo.MarkSent(ctx, n.ID)
		}
	}
}

func (s *Scheduler) startDailySummary(ctx context.Context) {
	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		for {
			now := time.Now()
			next := time.Date(now.Year(), now.Month(), now.Day(), 8, 0, 0, 0, now.Location())
			if now.After(next) {
				next = next.Add(24 * time.Hour)
			}
			delay := time.Until(next)
			log.Printf("daily summary: next run at %s (in %v)", next.Format("2006-01-02 15:04"), delay)

			select {
			case <-time.After(delay):
				s.sendDailySummary(ctx)
			case <-s.stopCh:
				return
			case <-ctx.Done():
				return
			}
		}
	}()
}

func (s *Scheduler) sendDailySummary(ctx context.Context) {
	log.Println("daily summary: starting")

	users, err := s.userRepo.GetDailySummaryUsers(ctx)
	if err != nil {
		log.Printf("daily summary: failed to get users: %v", err)
		return
	}

	yesterday := time.Now().Add(-24 * time.Hour)
	for _, user := range users {
		articles, err := s.articles.GetByUserSubscriptionsSince(ctx, user.ID, yesterday)
		if err != nil {
			log.Printf("daily summary: failed to get articles for user %s: %v", user.ID, err)
			continue
		}
		if len(articles) == 0 {
			continue
		}

		var awjList []*model.ArticleWithJournal
		for _, a := range articles {
			awjList = append(awjList, &model.ArticleWithJournal{
				Article:     *a,
				JournalName: a.JournalName,
			})
		}

		if err := s.wechatNtfr.SendSummary(ctx, user, awjList); err != nil {
			log.Printf("daily summary: send error for user %s: %v", user.ID, err)
		}

		for _, a := range articles {
			notif := &model.Notification{
				UserID:    user.ID,
				ArticleID: a.ID,
				Channel:   "wechat",
				Status:    "sent",
			}
			if err := s.notifRepo.Create(ctx, notif); err != nil {
				log.Printf("daily summary: create notification error: %v", err)
			}
		}
	}
}
