// internal/repo/user_repo.go
package repo

import (
	"context"
	"time"

	"github.com/humumu/journal-monitor/internal/model"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type UserRepo struct {
	pool *pgxpool.Pool
}

func NewUserRepo(pool *pgxpool.Pool) *UserRepo {
	return &UserRepo{pool: pool}
}

func (r *UserRepo) Create(ctx context.Context, user *model.User) error {
	query := `INSERT INTO users (email, password_hash, name, wechat_openid, push_frequency)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id, wechat_template_subscribed, created_at, updated_at`
	return r.pool.QueryRow(ctx, query,
		user.Email, user.PasswordHash, user.Name, user.WeChatOpenID, user.PushFrequency,
	).Scan(&user.ID, &user.WeChatTemplateSubscribed, &user.CreatedAt, &user.UpdatedAt)
}

func (r *UserRepo) GetByEmail(ctx context.Context, email string) (*model.User, error) {
	query := `SELECT id, email, password_hash, name, COALESCE(wechat_openid, ''),
		push_frequency, wechat_template_subscribed, created_at, updated_at FROM users WHERE email = $1`
	u := &model.User{}
	err := r.pool.QueryRow(ctx, query, email).Scan(
		&u.ID, &u.Email, &u.PasswordHash, &u.Name, &u.WeChatOpenID,
		&u.PushFrequency, &u.WeChatTemplateSubscribed, &u.CreatedAt, &u.UpdatedAt,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	return u, err
}

func (r *UserRepo) GetByWeChatOpenID(ctx context.Context, openID string) (*model.User, error) {
	query := `SELECT id, email, password_hash, name, COALESCE(wechat_openid, ''),
		push_frequency, wechat_template_subscribed, created_at, updated_at FROM users WHERE wechat_openid = $1`
	u := &model.User{}
	err := r.pool.QueryRow(ctx, query, openID).Scan(
		&u.ID, &u.Email, &u.PasswordHash, &u.Name, &u.WeChatOpenID,
		&u.PushFrequency, &u.WeChatTemplateSubscribed, &u.CreatedAt, &u.UpdatedAt,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	return u, err
}

func (r *UserRepo) GetByID(ctx context.Context, id string) (*model.User, error) {
	query := `SELECT id, email, password_hash, name, COALESCE(wechat_openid, ''),
		push_frequency, wechat_template_subscribed, created_at, updated_at FROM users WHERE id = $1`
	u := &model.User{}
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&u.ID, &u.Email, &u.PasswordHash, &u.Name, &u.WeChatOpenID,
		&u.PushFrequency, &u.WeChatTemplateSubscribed, &u.CreatedAt, &u.UpdatedAt,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	return u, err
}

func (r *UserRepo) UpdatePushFrequency(ctx context.Context, userID string, freq string) error {
	query := `UPDATE users SET push_frequency = $1, updated_at = $2 WHERE id = $3`
	ct, err := r.pool.Exec(ctx, query, freq, time.Now(), userID)
	if err != nil {
		return err
	}
	if ct.RowsAffected() == 0 {
		return pgx.ErrNoRows
	}
	return nil
}

func (r *UserRepo) LinkWeChat(ctx context.Context, userID string, openID string) error {
	query := `UPDATE users SET wechat_openid = $1, updated_at = $2 WHERE id = $3`
	ct, err := r.pool.Exec(ctx, query, openID, time.Now(), userID)
	if err != nil {
		return err
	}
	if ct.RowsAffected() == 0 {
		return pgx.ErrNoRows
	}
	return nil
}

func (r *UserRepo) GetTemplateSetting(ctx context.Context, userID string) (bool, error) {
	var subscribed bool
	err := r.pool.QueryRow(ctx,
		`SELECT wechat_template_subscribed FROM users WHERE id = $1`, userID,
	).Scan(&subscribed)
	if err == pgx.ErrNoRows {
		return false, nil
	}
	return subscribed, err
}

func (r *UserRepo) UpdateTemplateSetting(ctx context.Context, userID string, subscribed bool) error {
	query := `UPDATE users SET wechat_template_subscribed = $1, updated_at = NOW() WHERE id = $2`
	ct, err := r.pool.Exec(ctx, query, subscribed, userID)
	if err != nil {
		return err
	}
	if ct.RowsAffected() == 0 {
		return pgx.ErrNoRows
	}
	return nil
}

func (r *UserRepo) GetAll(ctx context.Context) ([]*model.User, error) {
	query := `SELECT id, email, password_hash, name, COALESCE(wechat_openid, ''),
		push_frequency, wechat_template_subscribed, created_at, updated_at FROM users`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var users []*model.User
	for rows.Next() {
		u := &model.User{}
		if err := rows.Scan(&u.ID, &u.Email, &u.PasswordHash, &u.Name, &u.WeChatOpenID,
			&u.PushFrequency, &u.WeChatTemplateSubscribed, &u.CreatedAt, &u.UpdatedAt); err != nil {
			return nil, err
		}
		users = append(users, u)
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return users, nil
}

func (r *UserRepo) GetDailySummaryUsers(ctx context.Context) ([]*model.User, error) {
	query := `SELECT id, email, password_hash, name, COALESCE(wechat_openid, ''),
		push_frequency, wechat_template_subscribed, created_at, updated_at
		FROM users WHERE push_frequency = 'daily'
		AND wechat_openid != '' AND wechat_template_subscribed = true`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var users []*model.User
	for rows.Next() {
		u := &model.User{}
		if err := rows.Scan(&u.ID, &u.Email, &u.PasswordHash, &u.Name, &u.WeChatOpenID,
			&u.PushFrequency, &u.WeChatTemplateSubscribed, &u.CreatedAt, &u.UpdatedAt); err != nil {
			return nil, err
		}
		users = append(users, u)
	}
	return users, rows.Err()
}
