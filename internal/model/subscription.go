package model

import "time"

type JournalSubscription struct {
	UserID    string    `json:"user_id"`
	JournalID string    `json:"journal_id"`
	CreatedAt time.Time `json:"created_at"`
}

type AuthorTracking struct {
	ID         string    `json:"id"`
	UserID     string    `json:"user_id"`
	AuthorName string    `json:"author_name"`
	CreatedAt  time.Time `json:"created_at"`
}

type KeywordSubscription struct {
	ID        string    `json:"id"`
	UserID    string    `json:"user_id"`
	Keyword   string    `json:"keyword"`
	CreatedAt time.Time `json:"created_at"`
}

type AuthorTrackingRequest struct {
	AuthorName string `json:"author_name" binding:"required"`
}

type KeywordSubscriptionRequest struct {
	Keyword string `json:"keyword" binding:"required"`
}

type UpdatePushFrequencyRequest struct {
	PushFrequency string `json:"push_frequency" binding:"required,oneof=realtime daily"`
}
