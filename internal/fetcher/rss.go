package fetcher

import (
	"context"
	"encoding/xml"
	"fmt"
	"net/http"
	"strings"
	"time"
)

type RSSSource struct {
	name   string
	url    string
	client *http.Client
}

func NewRSSSource(name, url string) *RSSSource {
	return &RSSSource{
		name: name,
		url:  url,
		client: &http.Client{Timeout: 30 * time.Second},
	}
}

func (s *RSSSource) Name() string { return s.name }

type rssFeed struct {
	Channel rssChannel `xml:"channel"`
}

type rssChannel struct {
	Items []rssItem `xml:"item"`
}

type rssItem struct {
	Title       string `xml:"title"`
	Link        string `xml:"link"`
	Description string `xml:"description"`
	DOI         string `xml:"doi"`
	Creator     string `xml:"dc:creator"`
	Date        string `xml:"dc:date"`
	PubDate     string `xml:"pubDate"`
}

func (s *RSSSource) Fetch(ctx context.Context) ([]RawArticle, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", s.url, nil)
	if err != nil {
		return nil, fmt.Errorf("rss request: %w", err)
	}
	req.Header.Set("User-Agent", "JournalMonitor/1.0")

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("rss fetch: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("rss status %d", resp.StatusCode)
	}

	var feed rssFeed
	if err := xml.NewDecoder(resp.Body).Decode(&feed); err != nil {
		return nil, fmt.Errorf("rss decode: %w", err)
	}

	var articles []RawArticle
	for _, item := range feed.Channel.Items {
		doi := item.DOI
		if doi == "" {
			doi = extractDOIFromURL(item.Link)
		}

		a := RawArticle{
			DOI:      doi,
			Title:    strings.TrimSpace(item.Title),
			Authors:  splitAuthors(item.Creator),
			Abstract: strings.TrimSpace(stripHTML(item.Description)),
			URL:      item.Link,
		}

		dateStr := item.Date
		if dateStr == "" {
			dateStr = item.PubDate
		}
		if t, err := parseDate(dateStr); err == nil {
			a.PublishDate = t.Format("2006-01-02")
		}

		if a.DOI != "" || a.Title != "" {
			articles = append(articles, a)
		}
	}

	return articles, nil
}

func extractDOIFromURL(url string) string {
	if strings.Contains(url, "doi.org/") {
		parts := strings.Split(url, "doi.org/")
		if len(parts) == 2 {
			return strings.TrimSpace(parts[1])
		}
	}
	return ""
}

func splitAuthors(authorStr string) []string {
	if authorStr == "" {
		return nil
	}
	parts := strings.Split(authorStr, ",")
	var authors []string
	for _, p := range parts {
		a := strings.TrimSpace(p)
		if a != "" {
			authors = append(authors, a)
		}
	}
	return authors
}

func parseDate(dateStr string) (time.Time, error) {
	formats := []string{
		time.RFC1123Z,
		time.RFC1123,
		time.RFC3339,
		"2006-01-02T15:04:05Z",
		"2006-01-02",
		"Mon, 2 Jan 2006 15:04:05 -0700",
	}
	for _, f := range formats {
		if t, err := time.Parse(f, dateStr); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("cannot parse date: %s", dateStr)
}

func stripHTML(s string) string {
	var result strings.Builder
	inTag := false
	for _, r := range s {
		if r == '<' {
			inTag = true
		} else if r == '>' {
			inTag = false
		} else if !inTag {
			result.WriteRune(r)
		}
	}
	return result.String()
}
