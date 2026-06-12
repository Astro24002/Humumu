// internal/repo/subscription_repo.go
package repo

import (
	"context"

	"github.com/humumu/journal-monitor/internal/model"
	"github.com/jackc/pgx/v5/pgxpool"
)

type SubscriptionRepo struct {
	pool *pgxpool.Pool
}

func NewSubscriptionRepo(pool *pgxpool.Pool) *SubscriptionRepo {
	return &SubscriptionRepo{pool: pool}
}

// Journal subscriptions

func (r *SubscriptionRepo) AddJournal(ctx context.Context, userID, journalID string) error {
	_, err := r.pool.Exec(ctx,
		`INSERT INTO journal_subscriptions (user_id, journal_id) VALUES ($1, $2)
		 ON CONFLICT DO NOTHING`, userID, journalID)
	return err
}

func (r *SubscriptionRepo) RemoveJournal(ctx context.Context, userID, journalID string) error {
	_, err := r.pool.Exec(ctx,
		`DELETE FROM journal_subscriptions WHERE user_id = $1 AND journal_id = $2`,
		userID, journalID)
	return err
}

func (r *SubscriptionRepo) GetUserJournals(ctx context.Context, userID string) ([]*model.Journal, error) {
	query := `SELECT j.id, j.name, j.slug, j.source_type, j.source_url,
		j.fetch_interval, j.is_active, j.created_by, j.created_at
		FROM journals j
		INNER JOIN journal_subscriptions js ON j.id = js.journal_id
		WHERE js.user_id = $1 AND j.is_active = true
		ORDER BY j.name`
	rows, err := r.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var journals []*model.Journal
	for rows.Next() {
		j := &model.Journal{}
		if err := rows.Scan(&j.ID, &j.Name, &j.Slug, &j.SourceType, &j.SourceURL,
			&j.FetchInterval, &j.IsActive, &j.CreatedBy, &j.CreatedAt); err != nil {
			return nil, err
		}
		journals = append(journals, j)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return journals, nil
}

func (r *SubscriptionRepo) GetJournalSubscriberIDs(ctx context.Context, journalID string) ([]string, error) {
	query := `SELECT user_id FROM journal_subscriptions WHERE journal_id = $1`
	rows, err := r.pool.Query(ctx, query, journalID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var ids []string
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return nil, err
		}
		ids = append(ids, id)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return ids, nil
}

// Author tracking

func (r *SubscriptionRepo) AddAuthor(ctx context.Context, userID, authorName string) error {
	_, err := r.pool.Exec(ctx,
		`INSERT INTO author_tracking (user_id, author_name) VALUES ($1, $2)
		 ON CONFLICT DO NOTHING`, userID, authorName)
	return err
}

func (r *SubscriptionRepo) RemoveAuthor(ctx context.Context, id string, userID string) error {
	_, err := r.pool.Exec(ctx,
		`DELETE FROM author_tracking WHERE id = $1 AND user_id = $2`, id, userID)
	return err
}

func (r *SubscriptionRepo) GetUserAuthors(ctx context.Context, userID string) ([]*model.AuthorTracking, error) {
	query := `SELECT id, user_id, author_name, created_at FROM author_tracking
		WHERE user_id = $1 ORDER BY created_at DESC`
	rows, err := r.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var authors []*model.AuthorTracking
	for rows.Next() {
		a := &model.AuthorTracking{}
		if err := rows.Scan(&a.ID, &a.UserID, &a.AuthorName, &a.CreatedAt); err != nil {
			return nil, err
		}
		authors = append(authors, a)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return authors, nil
}

func (r *SubscriptionRepo) GetAllTrackedAuthors(ctx context.Context) ([]*model.AuthorTracking, error) {
	query := `SELECT id, user_id, author_name, created_at FROM author_tracking`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var authors []*model.AuthorTracking
	for rows.Next() {
		a := &model.AuthorTracking{}
		if err := rows.Scan(&a.ID, &a.UserID, &a.AuthorName, &a.CreatedAt); err != nil {
			return nil, err
		}
		authors = append(authors, a)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return authors, nil
}

// Keyword subscriptions

func (r *SubscriptionRepo) AddKeyword(ctx context.Context, userID, keyword string) error {
	_, err := r.pool.Exec(ctx,
		`INSERT INTO keyword_subscriptions (user_id, keyword) VALUES ($1, $2)
		 ON CONFLICT DO NOTHING`, userID, keyword)
	return err
}

func (r *SubscriptionRepo) RemoveKeyword(ctx context.Context, id string, userID string) error {
	_, err := r.pool.Exec(ctx,
		`DELETE FROM keyword_subscriptions WHERE id = $1 AND user_id = $2`, id, userID)
	return err
}

func (r *SubscriptionRepo) GetUserKeywords(ctx context.Context, userID string) ([]*model.KeywordSubscription, error) {
	query := `SELECT id, user_id, keyword, created_at FROM keyword_subscriptions
		WHERE user_id = $1 ORDER BY created_at DESC`
	rows, err := r.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var keywords []*model.KeywordSubscription
	for rows.Next() {
		k := &model.KeywordSubscription{}
		if err := rows.Scan(&k.ID, &k.UserID, &k.Keyword, &k.CreatedAt); err != nil {
			return nil, err
		}
		keywords = append(keywords, k)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return keywords, nil
}

func (r *SubscriptionRepo) GetAllKeywords(ctx context.Context) ([]*model.KeywordSubscription, error) {
	query := `SELECT id, user_id, keyword, created_at FROM keyword_subscriptions`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var keywords []*model.KeywordSubscription
	for rows.Next() {
		k := &model.KeywordSubscription{}
		if err := rows.Scan(&k.ID, &k.UserID, &k.Keyword, &k.CreatedAt); err != nil {
			return nil, err
		}
		keywords = append(keywords, k)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return keywords, nil
}
