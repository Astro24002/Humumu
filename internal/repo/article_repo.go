// internal/repo/article_repo.go
package repo

import (
	"context"
	"time"

	"github.com/humumu/journal-monitor/internal/model"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type ArticleRepo struct {
	pool *pgxpool.Pool
}

func NewArticleRepo(pool *pgxpool.Pool) *ArticleRepo {
	return &ArticleRepo{pool: pool}
}

func (r *ArticleRepo) Create(ctx context.Context, a *model.Article) error {
	query := `INSERT INTO articles (doi, title, authors, abstract, journal_id, publish_date, url)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING id, fetched_at`

	// Pass nil for empty DOI so the nullable column stores NULL,
	// avoiding UNIQUE(doi, journal_id) conflicts for sources without DOIs (e.g., CNKI)
	var doi interface{}
	if a.DOI == "" {
		doi = nil
	} else {
		doi = a.DOI
	}

	return r.pool.QueryRow(ctx, query,
		doi, a.Title, a.Authors, a.Abstract, a.JournalID, a.PublishDate, a.URL,
	).Scan(&a.ID, &a.FetchedAt)
}

func (r *ArticleRepo) ExistsByDOI(ctx context.Context, doi string, journalID string) (bool, error) {
	query := `SELECT EXISTS(SELECT 1 FROM articles WHERE doi = $1 AND journal_id = $2)`
	var exists bool
	err := r.pool.QueryRow(ctx, query, doi, journalID).Scan(&exists)
	return exists, err
}

func (r *ArticleRepo) GetAll(ctx context.Context, limit, offset int) ([]*model.Article, error) {
	query := `SELECT a.id, COALESCE(a.doi, ''), a.title, a.authors, COALESCE(a.abstract,''),
		a.journal_id, a.publish_date, a.url, a.fetched_at,
		COALESCE(j.name, ''), COALESCE(j.source_type, '')
		FROM articles a
		LEFT JOIN journals j ON a.journal_id = j.id
		ORDER BY a.publish_date DESC NULLS LAST, a.fetched_at DESC
		LIMIT $1 OFFSET $2`
	rows, err := r.pool.Query(ctx, query, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanArticles(rows)
}

func (r *ArticleRepo) GetByJournal(ctx context.Context, journalID string, limit, offset int) ([]*model.Article, error) {
	query := `SELECT a.id, COALESCE(a.doi, ''), a.title, a.authors, COALESCE(a.abstract,''),
		a.journal_id, a.publish_date, a.url, a.fetched_at,
		COALESCE(j.name, ''), COALESCE(j.source_type, '')
		FROM articles a
		LEFT JOIN journals j ON a.journal_id = j.id
		WHERE a.journal_id = $1
		ORDER BY a.publish_date DESC NULLS LAST, a.fetched_at DESC
		LIMIT $2 OFFSET $3`
	rows, err := r.pool.Query(ctx, query, journalID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanArticles(rows)
}

func (r *ArticleRepo) GetByUserSubscriptions(ctx context.Context, userID string, limit, offset int) ([]*model.Article, error) {
	query := `SELECT a.id, COALESCE(a.doi, ''), a.title, a.authors, COALESCE(a.abstract,''),
		a.journal_id, a.publish_date, a.url, a.fetched_at,
		COALESCE(j.name, ''), COALESCE(j.source_type, '')
		FROM articles a
		INNER JOIN journal_subscriptions js ON a.journal_id = js.journal_id
		LEFT JOIN journals j ON a.journal_id = j.id
		WHERE js.user_id = $1
		ORDER BY a.publish_date DESC NULLS LAST, a.fetched_at DESC
		LIMIT $2 OFFSET $3`
	rows, err := r.pool.Query(ctx, query, userID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanArticles(rows)
}

func (r *ArticleRepo) GetByID(ctx context.Context, id string) (*model.Article, error) {
	query := `SELECT a.id, COALESCE(a.doi, ''), a.title, a.authors, COALESCE(a.abstract,''),
		a.journal_id, a.publish_date, a.url, a.fetched_at,
		COALESCE(j.name, ''), COALESCE(j.source_type, '')
		FROM articles a
		LEFT JOIN journals j ON a.journal_id = j.id
		WHERE a.id = $1`
	a := &model.Article{}
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&a.ID, &a.DOI, &a.Title, &a.Authors, &a.Abstract,
		&a.JournalID, &a.PublishDate, &a.URL, &a.FetchedAt,
		&a.JournalName, &a.JournalSourceType,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	return a, err
}

func scanArticles(rows pgx.Rows) ([]*model.Article, error) {
	var articles []*model.Article
	for rows.Next() {
		a := &model.Article{}
		if err := rows.Scan(&a.ID, &a.DOI, &a.Title, &a.Authors, &a.Abstract,
			&a.JournalID, &a.PublishDate, &a.URL, &a.FetchedAt,
			&a.JournalName, &a.JournalSourceType); err != nil {
			return nil, err
		}
		articles = append(articles, a)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return articles, nil
}

func (r *ArticleRepo) GetArticlesSince(ctx context.Context, journalID string, since time.Time) ([]*model.Article, error) {
	query := `SELECT a.id, COALESCE(a.doi, ''), a.title, a.authors, COALESCE(a.abstract,''),
		a.journal_id, a.publish_date, a.url, a.fetched_at,
		COALESCE(j.name, ''), COALESCE(j.source_type, '')
		FROM articles a
		LEFT JOIN journals j ON a.journal_id = j.id
		WHERE a.journal_id = $1 AND a.fetched_at >= $2
		ORDER BY a.fetched_at ASC`
	rows, err := r.pool.Query(ctx, query, journalID, since)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanArticles(rows)
}

func (r *ArticleRepo) CountAll(ctx context.Context) (int, error) {
	var count int
	err := r.pool.QueryRow(ctx, `SELECT COUNT(*) FROM articles`).Scan(&count)
	return count, err
}

func (r *ArticleRepo) GetByUserSubscriptionsSince(ctx context.Context, userID string, since time.Time) ([]*model.Article, error) {
	query := `SELECT a.id, COALESCE(a.doi, ''), a.title, a.authors, COALESCE(a.abstract,''),
		a.journal_id, a.publish_date, a.url, a.fetched_at,
		COALESCE(j.name, ''), COALESCE(j.source_type, '')
		FROM articles a
		INNER JOIN journal_subscriptions js ON a.journal_id = js.journal_id
		LEFT JOIN journals j ON a.journal_id = j.id
		WHERE js.user_id = $1 AND a.fetched_at >= $2
		ORDER BY a.fetched_at ASC`
	rows, err := r.pool.Query(ctx, query, userID, since)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanArticles(rows)
}
