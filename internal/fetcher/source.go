package fetcher

import "context"

type RawArticle struct {
	DOI         string
	Title       string
	Authors     []string
	Abstract    string
	PublishDate string // "2006-01-02" or empty
	URL         string
}

type Source interface {
	Name() string
	Fetch(ctx context.Context) ([]RawArticle, error)
}
