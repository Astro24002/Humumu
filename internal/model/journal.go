package model

import "time"

type Journal struct {
	ID            string    `json:"id"`
	Name          string    `json:"name"`
	Slug          string    `json:"slug"`
	SourceType    string    `json:"source_type"` // "rss" | "arxiv" | "crossref"
	SourceURL     string    `json:"source_url"`
	FetchInterval time.Duration `json:"fetch_interval"`
	IsActive      bool      `json:"is_active"`
	CreatedBy     *string   `json:"created_by,omitempty"`
	CreatedAt     time.Time `json:"created_at"`
}

type JournalRequest struct {
	ID          string     `json:"id"`
	UserID      string     `json:"user_id"`
	JournalName string     `json:"journal_name"`
	SourceURL   string     `json:"source_url"`
	Status      string     `json:"status"` // "pending" | "approved" | "rejected"
	CreatedAt   time.Time  `json:"created_at"`
	ReviewedAt  *time.Time `json:"reviewed_at,omitempty"`
}

type CreateJournalRequest struct {
	JournalName string `json:"journal_name" binding:"required"`
	SourceURL   string `json:"source_url" binding:"required,url"`
}
