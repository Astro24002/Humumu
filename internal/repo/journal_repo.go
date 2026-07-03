// internal/repo/journal_repo.go
package repo

import (
	"context"
	"time"

	"github.com/humumu/journal-monitor/internal/model"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type JournalRepo struct {
	pool *pgxpool.Pool
}

func NewJournalRepo(pool *pgxpool.Pool) *JournalRepo {
	return &JournalRepo{pool: pool}
}

func (r *JournalRepo) GetAllActive(ctx context.Context) ([]*model.Journal, error) {
	query := `SELECT j.id, j.name, j.slug, j.source_type, j.source_url,
		COALESCE(j.description, ''), j.fetch_interval, j.is_active, j.created_by, j.created_at,
		COALESCE(jstats.article_count, 0), jstats.last_article_date
		FROM journals j
		LEFT JOIN LATERAL (
			SELECT COUNT(*) AS article_count, MAX(publish_date) AS last_article_date
			FROM articles WHERE journal_id = j.id
		) jstats ON true
		WHERE j.is_active = true ORDER BY j.name`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanJournals(rows)
}

func (r *JournalRepo) GetByID(ctx context.Context, id string) (*model.Journal, error) {
	query := `SELECT j.id, j.name, j.slug, j.source_type, j.source_url,
		COALESCE(j.description, ''), j.fetch_interval, j.is_active, j.created_by, j.created_at,
		COALESCE(jstats.article_count, 0), jstats.last_article_date
		FROM journals j
		LEFT JOIN LATERAL (
			SELECT COUNT(*) AS article_count, MAX(publish_date) AS last_article_date
			FROM articles WHERE journal_id = j.id
		) jstats ON true
		WHERE j.id = $1`
	j := &model.Journal{}
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&j.ID, &j.Name, &j.Slug, &j.SourceType, &j.SourceURL,
		&j.Description, &j.FetchInterval, &j.IsActive, &j.CreatedBy, &j.CreatedAt,
		&j.ArticleCount, &j.LastArticleDate,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	return j, err
}

func (r *JournalRepo) Create(ctx context.Context, j *model.Journal) error {
	query := `INSERT INTO journals (name, slug, source_type, source_url, description, fetch_interval, created_by)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING id, created_at`
	return r.pool.QueryRow(ctx, query,
		j.Name, j.Slug, j.SourceType, j.SourceURL, j.Description, j.FetchInterval, j.CreatedBy,
	).Scan(&j.ID, &j.CreatedAt)
}

func (r *JournalRepo) FindByURL(ctx context.Context, sourceURL string) (*model.Journal, error) {
	query := `SELECT j.id, j.name, j.slug, j.source_type, j.source_url,
		COALESCE(j.description, ''), j.fetch_interval, j.is_active, j.created_by, j.created_at,
		COALESCE(jstats.article_count, 0), jstats.last_article_date
		FROM journals j
		LEFT JOIN LATERAL (
			SELECT COUNT(*) AS article_count, MAX(publish_date) AS last_article_date
			FROM articles WHERE journal_id = j.id
		) jstats ON true
		WHERE j.source_url = $1
		LIMIT 1`
	j := &model.Journal{}
	err := r.pool.QueryRow(ctx, query, sourceURL).Scan(
		&j.ID, &j.Name, &j.Slug, &j.SourceType, &j.SourceURL,
		&j.Description, &j.FetchInterval, &j.IsActive, &j.CreatedBy, &j.CreatedAt,
		&j.ArticleCount, &j.LastArticleDate,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	return j, err
}

func (r *JournalRepo) GetAll(ctx context.Context) ([]*model.Journal, error) {
	query := `SELECT j.id, j.name, j.slug, j.source_type, j.source_url,
		COALESCE(j.description, ''), j.fetch_interval, j.is_active, j.created_by, j.created_at,
		COALESCE(jstats.article_count, 0), jstats.last_article_date
		FROM journals j
		LEFT JOIN LATERAL (
			SELECT COUNT(*) AS article_count, MAX(publish_date) AS last_article_date
			FROM articles WHERE journal_id = j.id
		) jstats ON true
		ORDER BY j.name`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanJournals(rows)
}

// helper to scan journal rows with stats
func scanJournals(rows pgx.Rows) ([]*model.Journal, error) {
	var journals []*model.Journal
	for rows.Next() {
		j := &model.Journal{}
		if err := rows.Scan(&j.ID, &j.Name, &j.Slug, &j.SourceType, &j.SourceURL,
			&j.Description, &j.FetchInterval, &j.IsActive, &j.CreatedBy, &j.CreatedAt,
			&j.ArticleCount, &j.LastArticleDate); err != nil {
			return nil, err
		}
		journals = append(journals, j)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return journals, nil
}

// Journal request operations

func (r *JournalRepo) CreateRequest(ctx context.Context, req *model.JournalRequest) error {
	query := `INSERT INTO journal_requests (user_id, journal_name, source_url)
		VALUES ($1, $2, $3) RETURNING id, created_at`
	return r.pool.QueryRow(ctx, query, req.UserID, req.JournalName, req.SourceURL).
		Scan(&req.ID, &req.CreatedAt)
}

func (r *JournalRepo) GetRequestsByUser(ctx context.Context, userID string) ([]*model.JournalRequest, error) {
	query := `SELECT id, user_id, journal_name, source_url, status, created_at, reviewed_at
		FROM journal_requests WHERE user_id = $1 ORDER BY created_at DESC`
	rows, err := r.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var reqs []*model.JournalRequest
	for rows.Next() {
		req := &model.JournalRequest{}
		if err := rows.Scan(&req.ID, &req.UserID, &req.JournalName, &req.SourceURL,
			&req.Status, &req.CreatedAt, &req.ReviewedAt); err != nil {
			return nil, err
		}
		reqs = append(reqs, req)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return reqs, nil
}

func (r *JournalRepo) UpdateRequestStatus(ctx context.Context, reqID, status string) error {
	query := `UPDATE journal_requests SET status = $1, reviewed_at = $2 WHERE id = $3`
	ct, err := r.pool.Exec(ctx, query, status, time.Now(), reqID)
	if err != nil {
		return err
	}
	if ct.RowsAffected() == 0 {
		return pgx.ErrNoRows
	}
	return nil
}

func (r *JournalRepo) Update(ctx context.Context, id string, j *model.Journal) error {
	query := `UPDATE journals SET name=$1, slug=$2, source_type=$3, source_url=$4, description=$5, is_active=$6 WHERE id=$7`
	_, err := r.pool.Exec(ctx, query, j.Name, j.Slug, j.SourceType, j.SourceURL, j.Description, j.IsActive, id)
	return err
}

func (r *JournalRepo) Delete(ctx context.Context, id string) error {
	_, err := r.pool.Exec(ctx, `DELETE FROM journals WHERE id=$1`, id)
	return err
}

func (r *JournalRepo) GetAllRequests(ctx context.Context) ([]*model.JournalRequest, error) {
	query := `SELECT id, user_id, journal_name, source_url, status, created_at, reviewed_at
		FROM journal_requests ORDER BY created_at DESC`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var reqs []*model.JournalRequest
	for rows.Next() {
		req := &model.JournalRequest{}
		if err := rows.Scan(&req.ID, &req.UserID, &req.JournalName, &req.SourceURL,
			&req.Status, &req.CreatedAt, &req.ReviewedAt); err != nil {
			return nil, err
		}
		reqs = append(reqs, req)
	}
	return reqs, nil
}

func (r *JournalRepo) CountPendingRequests(ctx context.Context) (int, error) {
	var count int
	err := r.pool.QueryRow(ctx, `SELECT COUNT(*) FROM journal_requests WHERE status='pending'`).Scan(&count)
	return count, err
}
