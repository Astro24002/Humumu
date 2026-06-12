package model

import "time"

type Article struct {
	ID          string    `json:"id"`
	DOI         string    `json:"doi"`
	Title       string    `json:"title"`
	Authors     []string  `json:"authors"`
	Abstract    string    `json:"abstract"`
	JournalID   string    `json:"journal_id"`
	PublishDate *time.Time `json:"publish_date,omitempty"`
	URL         string    `json:"url"`
	FetchedAt   time.Time `json:"fetched_at"`
}
