// internal/repo/notification_repo.go
package repo

import (
	"context"
	"time"

	"github.com/humumu/journal-monitor/internal/model"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type NotificationRepo struct {
	pool *pgxpool.Pool
}

func NewNotificationRepo(pool *pgxpool.Pool) *NotificationRepo {
	return &NotificationRepo{pool: pool}
}

func (r *NotificationRepo) Create(ctx context.Context, n *model.Notification) error {
	query := `INSERT INTO notifications (user_id, article_id, channel, status)
		VALUES ($1, $2, $3, $4) RETURNING id, created_at`
	return r.pool.QueryRow(ctx, query,
		n.UserID, n.ArticleID, n.Channel, n.Status,
	).Scan(&n.ID, &n.CreatedAt)
}

func (r *NotificationRepo) MarkSent(ctx context.Context, id string) error {
	query := `UPDATE notifications SET status = 'sent', sent_at = $1 WHERE id = $2`
	ct, err := r.pool.Exec(ctx, query, time.Now(), id)
	if err != nil {
		return err
	}
	if ct.RowsAffected() == 0 {
		return pgx.ErrNoRows
	}
	return nil
}

func (r *NotificationRepo) MarkFailed(ctx context.Context, id string, errMsg string) error {
	query := `UPDATE notifications SET status = 'failed', error_message = $1 WHERE id = $2`
	ct, err := r.pool.Exec(ctx, query, errMsg, id)
	if err != nil {
		return err
	}
	if ct.RowsAffected() == 0 {
		return pgx.ErrNoRows
	}
	return nil
}

func (r *NotificationRepo) GetPending(ctx context.Context) ([]*model.Notification, error) {
	query := `SELECT id, user_id, article_id, channel, status, error_message, created_at, sent_at
		FROM notifications WHERE status = 'pending' ORDER BY created_at ASC LIMIT 100`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var notifs []*model.Notification
	for rows.Next() {
		n := &model.Notification{}
		if err := rows.Scan(&n.ID, &n.UserID, &n.ArticleID, &n.Channel,
			&n.Status, &n.ErrorMessage, &n.CreatedAt, &n.SentAt); err != nil {
			return nil, err
		}
		notifs = append(notifs, n)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return notifs, nil
}

func (r *NotificationRepo) GetByUser(ctx context.Context, userID string, limit, offset int) ([]*model.Notification, error) {
	query := `SELECT id, user_id, article_id, channel, status, error_message, created_at, sent_at
		FROM notifications WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3`
	rows, err := r.pool.Query(ctx, query, userID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var notifs []*model.Notification
	for rows.Next() {
		n := &model.Notification{}
		if err := rows.Scan(&n.ID, &n.UserID, &n.ArticleID, &n.Channel,
			&n.Status, &n.ErrorMessage, &n.CreatedAt, &n.SentAt); err != nil {
			return nil, err
		}
		notifs = append(notifs, n)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return notifs, nil
}

func (r *NotificationRepo) GetArticleWithJournal(ctx context.Context, articleID string) (*model.ArticleWithJournal, error) {
	query := `SELECT a.id, a.doi, a.title, a.authors, COALESCE(a.abstract,''),
		a.journal_id, a.publish_date, a.url, a.fetched_at,
		j.name, j.slug
		FROM articles a
		INNER JOIN journals j ON a.journal_id = j.id
		WHERE a.id = $1`
	awj := &model.ArticleWithJournal{}
	err := r.pool.QueryRow(ctx, query, articleID).Scan(
		&awj.ID, &awj.DOI, &awj.Title, &awj.Authors, &awj.Abstract,
		&awj.JournalID, &awj.PublishDate, &awj.URL, &awj.FetchedAt,
		&awj.JournalName, &awj.JournalSlug,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	return awj, err
}
