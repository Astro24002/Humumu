package matcher

import (
	"context"
	"log"

	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/repo"
)

type MatchResult struct {
	UserID    string
	ArticleID string
	Channel   string
}

type Engine struct {
	subRepo  *repo.SubscriptionRepo
	userRepo *repo.UserRepo
}

func NewEngine(subRepo *repo.SubscriptionRepo, userRepo *repo.UserRepo) *Engine {
	return &Engine{
		subRepo:  subRepo,
		userRepo: userRepo,
	}
}

func (e *Engine) Match(ctx context.Context, article *model.Article) []MatchResult {
	var results []MatchResult

	subscribers, err := e.subRepo.GetJournalSubscriberIDs(ctx, article.JournalID)
	if err != nil {
		log.Printf("matcher: failed to get journal subscribers: %v", err)
	} else {
		for _, uid := range subscribers {
			results = append(results, MatchResult{
				UserID:    uid,
				ArticleID: article.ID,
				Channel:   "email",
			})
		}
	}

	authorMatches, err := e.matchAuthors(ctx, article)
	if err != nil {
		log.Printf("matcher: author match error: %v", err)
	} else {
		results = append(results, authorMatches...)
	}

	keywordMatches, err := e.matchKeywords(ctx, article)
	if err != nil {
		log.Printf("matcher: keyword match error: %v", err)
	} else {
		results = append(results, keywordMatches...)
	}

	results = dedupResults(results)

	for i, r := range results {
		results[i].Channel = e.resolveChannel(ctx, r.UserID)
	}

	return results
}

func dedupResults(results []MatchResult) []MatchResult {
	seen := make(map[string]bool)
	var deduped []MatchResult
	for _, r := range results {
		key := r.UserID + ":" + r.ArticleID
		if seen[key] {
			continue
		}
		seen[key] = true
		deduped = append(deduped, r)
	}
	return deduped
}

func (e *Engine) resolveChannel(ctx context.Context, userID string) string {
	user, err := e.userRepo.GetByID(ctx, userID)
	if err != nil || user == nil {
		return "email"
	}
	if user.WeChatOpenID != "" {
		return "wechat"
	}
	return "email"
}
