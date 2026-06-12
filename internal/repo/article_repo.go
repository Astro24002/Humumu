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
	return r.pool.QueryRow(ctx, query,
		a.DOI, a.Title, a.Authors, a.Abstract, a.JournalID, a.PublishDate, a.URL,
	).Scan(&a.ID, &a.FetchedAt)
}

func (r *ArticleRepo) ExistsByDOI(ctx context.Context, doi string, journalID string) (bool, error) {
	query := `SELECT EXISTS(SELECT 1 FROM articles WHERE doi = $1 AND journal_id = $2)`
	var exists bool
	err := r.pool.QueryRow(ctx, query, doi, journalID).Scan(&exists)
	return exists, err
}

func (r *ArticleRepo) GetByJournal(ctx context.Context, journalID string, limit, offset int) ([]*model.Article, error) {
	query := `SELECT id, doi, title, authors, COALESCE(abstract,''),
		journal_id, publish_date, url, fetched_at
		FROM articles WHERE journal_id = $1
		ORDER BY publish_date DESC NULLS LAST, fetched_at DESC
		LIMIT $2 OFFSET $3`
	rows, err := r.pool.Query(ctx, query, journalID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanArticles(rows)
}

func (r *ArticleRepo) GetByUserSubscriptions(ctx context.Context, userID string, limit, offset int) ([]*model.Article, error) {
	query := `SELECT a.id, a.doi, a.title, a.authors, COALESCE(a.abstract,''),
		a.journal_id, a.publish_date, a.url, a.fetched_at
		FROM articles a
		INNER JOIN journal_subscriptions js ON a.journal_id = js.journal_id
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
	query := `SELECT id, doi, title, authors, COALESCE(abstract,''),
		journal_id, publish_date, url, fetched_at
		FROM articles WHERE id = $1`
	a := &model.Article{}
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&a.ID, &a.DOI, &a.Title, &a.Authors, &a.Abstract,
		&a.JournalID, &a.PublishDate, &a.URL, &a.FetchedAt,
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
			&a.JournalID, &a.PublishDate, &a.URL, &a.FetchedAt); err != nil {
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
	query := `SELECT a.id, a.doi, a.title, a.authors, COALESCE(a.abstract,''),
		a.journal_id, a.publish_date, a.url, a.fetched_at
		FROM articles a
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
