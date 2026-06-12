package fetcher

import (
	"context"
	"encoding/xml"
	"fmt"
	"net/http"
	"strings"
	"time"
)

type ArxivSource struct {
	name     string
	category string
	client   *http.Client
}

func NewArxivSource(name, category string) *ArxivSource {
	return &ArxivSource{
		name:     name,
		category: category,
		client:   &http.Client{Timeout: 30 * time.Second},
	}
}

func (s *ArxivSource) Name() string { return s.name }

type atomFeed struct {
	XMLName xml.Name   `xml:"feed"`
	Entries []atomEntry `xml:"entry"`
}

type atomEntry struct {
	ID        string      `xml:"id"`
	Title     string      `xml:"title"`
	Summary   string      `xml:"summary"`
	Published string      `xml:"published"`
	Updated   string      `xml:"updated"`
	Authors   []atomAuthor `xml:"author"`
	Links     []atomLink   `xml:"link"`
}

type atomAuthor struct {
	Name string `xml:"name"`
}

type atomLink struct {
	Href  string `xml:"href,attr"`
	Rel   string `xml:"rel,attr"`
	Title string `xml:"title,attr"`
}

func (s *ArxivSource) Fetch(ctx context.Context) ([]RawArticle, error) {
	url := fmt.Sprintf("http://export.arxiv.org/api/query?search_query=cat:%s&sortBy=submittedDate&sortOrder=descending&max_results=100",
		s.category)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("arxiv request: %w", err)
	}
	req.Header.Set("User-Agent", "JournalMonitor/1.0")

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("arxiv fetch: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("arxiv status %d", resp.StatusCode)
	}

	var feed atomFeed
	if err := xml.NewDecoder(resp.Body).Decode(&feed); err != nil {
		return nil, fmt.Errorf("arxiv decode: %w", err)
	}

	var articles []RawArticle
	for _, entry := range feed.Entries {
		doi := extractArxivDOI(entry.ID)

		var authors []string
		for _, a := range entry.Authors {
			authors = append(authors, strings.TrimSpace(a.Name))
		}

		articleURL := entry.ID
		for _, l := range entry.Links {
			if l.Rel == "alternate" {
				articleURL = l.Href
				break
			}
		}

		a := RawArticle{
			DOI:      doi,
			Title:    strings.TrimSpace(strings.ReplaceAll(entry.Title, "\n", " ")),
			Authors:  authors,
			Abstract: strings.TrimSpace(entry.Summary),
			URL:      articleURL,
		}

		if t, err := time.Parse(time.RFC3339, entry.Published); err == nil {
			a.PublishDate = t.Format("2006-01-02")
		}

		if a.DOI != "" || a.Title != "" {
			articles = append(articles, a)
		}
	}

	return articles, nil
}

func extractArxivDOI(id string) string {
	id = strings.TrimSuffix(id, "/")
	parts := strings.Split(id, "/")
	if len(parts) == 0 {
		return ""
	}
	last := parts[len(parts)-1]
	if idx := strings.LastIndex(last, "v"); idx > 0 {
		last = last[:idx]
	}
	return last
}
