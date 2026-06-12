package model

import "time"

type Notification struct {
	ID           string     `json:"id"`
	UserID       string     `json:"user_id"`
	ArticleID    string     `json:"article_id"`
	Channel      string     `json:"channel"` // "email" | "wechat"
	Status       string     `json:"status"`  // "pending" | "sent" | "failed"
	ErrorMessage *string    `json:"error_message,omitempty"`
	CreatedAt    time.Time  `json:"created_at"`
	SentAt       *time.Time `json:"sent_at,omitempty"`
}

// ArticleWithJournal is used for notifications — joins article + journal
type ArticleWithJournal struct {
	Article
	JournalName string `json:"journal_name"`
	JournalSlug string `json:"journal_slug"`
}
