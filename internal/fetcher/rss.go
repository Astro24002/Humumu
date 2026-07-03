package fetcher

import (
	"bytes"
	"context"
	"encoding/xml"
	"fmt"
	"io"
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

// --- Common item used by all parsers ---

type rssItem struct {
	Title       string `xml:"title"`
	Link        string `xml:"link"`
	Description string `xml:"description"`
	DOI         string `xml:"doi"`
	Creator     string `xml:"http://purl.org/dc/elements/1.1/ creator"`
	Date        string `xml:"http://purl.org/dc/elements/1.1/ date"`
	PubDate     string `xml:"pubDate"`
}

// --- RSS 2.0 parser (<rss version="2.0"><channel><item>) ---

type rss20Feed struct {
	Channel rss20Channel `xml:"channel"`
}

type rss20Channel struct {
	Items []rssItem `xml:"item"`
}

func parseRSS20(dec *xml.Decoder) ([]RawArticle, error) {
	var feed rss20Feed
	if err := dec.Decode(&feed); err != nil {
		return nil, fmt.Errorf("rss20 decode: %w", err)
	}
	return itemsToArticles(feed.Channel.Items), nil
}

// --- RDF/RSS 1.0 parser (<rdf:RDF><channel>...<item rdf:about="...">) ---

type rdfFeed struct {
	Channel rdfChannel    `xml:"channel"`
	Items   []rdfItem     `xml:"item"`
}

type rdfChannel struct {
	Title       string `xml:"title"`
	Link        string `xml:"link"`
	Description string `xml:"description"`
}

type rdfItem struct {
	Title       string `xml:"title"`
	Link        string `xml:"link"`
	Description string `xml:"description"`
	Creator     string `xml:"http://purl.org/dc/elements/1.1/ creator"`
	Date        string `xml:"http://purl.org/dc/elements/1.1/ date"`
	DOI         string `xml:"doi"`
	PubDate     string `xml:"pubDate"`
}

func parseRDF(dec *xml.Decoder) ([]RawArticle, error) {
	var feed rdfFeed
	if err := dec.Decode(&feed); err != nil {
		return nil, fmt.Errorf("rdf decode: %w", err)
	}
	var items []rssItem
	for _, it := range feed.Items {
		items = append(items, rssItem{
			Title:       it.Title,
			Link:        it.Link,
			Description: it.Description,
			Creator:     it.Creator,
			Date:        it.Date,
			PubDate:     it.PubDate,
			DOI:         it.DOI,
		})
	}
	return itemsToArticles(items), nil
}

// --- Atom parser (<feed><entry>) ---

type atomFeed struct {
	Entries []atomEntry `xml:"entry"`
}

type atomEntry struct {
	ID        string       `xml:"id"`
	Title     string       `xml:"title"`
	Summary   string       `xml:"summary"`
	Published string       `xml:"published"`
	Authors   []atomAuthor `xml:"author"`
	Links     []atomLink   `xml:"link"`
}

type atomAuthor struct {
	Name string `xml:"name"`
}

type atomLink struct {
	Href  string `xml:"href,attr"`
	Rel   string `xml:"rel,attr"`
}

func parseAtom(dec *xml.Decoder) ([]RawArticle, error) {
	var feed atomFeed
	if err := dec.Decode(&feed); err != nil {
		return nil, fmt.Errorf("atom decode: %w", err)
	}
	var articles []RawArticle
	for _, entry := range feed.Entries {
		doi := extractDOIFromURL(entry.ID)
		var authors []string
		for _, a := range entry.Authors {
			authors = append(authors, strings.TrimSpace(a.Name))
		}
		articleURL := ""
		for _, l := range entry.Links {
			if l.Rel == "alternate" || l.Rel == "" {
				articleURL = l.Href
				break
			}
		}
		a := RawArticle{
			DOI:      doi,
			Title:    strings.TrimSpace(entry.Title),
			Authors:  authors,
			Abstract: strings.TrimSpace(stripHTML(entry.Summary)),
			URL:      articleURL,
		}
		if t, err := time.Parse(time.RFC3339, entry.Published); err == nil {
			a.PublishDate = t.Format("2006-01-02")
		} else if t, err := time.Parse("2006-01-02T15:04:05Z", entry.Published); err == nil {
			a.PublishDate = t.Format("2006-01-02")
		}
		if a.DOI != "" || a.Title != "" {
			articles = append(articles, a)
		}
	}
	return articles, nil
}

// --- Common: convert rssItem list to RawArticle list ---

func itemsToArticles(items []rssItem) []RawArticle {
	var articles []RawArticle
	for _, item := range items {
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
	return articles
}

// --- Fetch: detect format and dispatch ---

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

	// Read the first 1KB to detect format, then create a teereader
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("rss read: %w", err)
	}

	// Detect format by scanning the root element
	peek := string(body)
	var parsed []RawArticle

	switch {
	case strings.Contains(peek, "<feed") || strings.Contains(peek, "<Feed"):
		parsed, err = parseAtom(xml.NewDecoder(bytes.NewReader(body)))
	case strings.Contains(peek, "<rdf:RDF") || strings.Contains(peek, "<RDF"):
		parsed, err = parseRDF(xml.NewDecoder(bytes.NewReader(body)))
	default:
		// Assume RSS 2.0
		parsed, err = parseRSS20(xml.NewDecoder(bytes.NewReader(body)))
	}

	if err != nil {
		return nil, fmt.Errorf("feed parse: %w", err)
	}
	return parsed, nil
}

// --- Feed metadata extraction ---

// FeedMeta holds basic info about a feed needed for journal creation.
type FeedMeta struct {
	Title      string
	SourceType string // "rss", "atom", "rdf"
}

// FetchFeedMeta fetches a feed URL and extracts the feed title and format type
// without parsing individual articles. Used for journal preview/creation.
func FetchFeedMeta(ctx context.Context, url string) (*FeedMeta, error) {
	client := &http.Client{Timeout: 30 * time.Second}
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("feed meta request: %w", err)
	}
	req.Header.Set("User-Agent", "JournalMonitor/1.0")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("feed meta fetch: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("feed meta status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("feed meta read: %w", err)
	}

	peek := string(body)

	// Try Atom first (<feed>)
	if strings.Contains(peek, "<feed") || strings.Contains(peek, "<Feed") {
		var feed struct {
			Title string `xml:"title"`
		}
		if err := xml.NewDecoder(bytes.NewReader(body)).Decode(&feed); err == nil && feed.Title != "" {
			return &FeedMeta{Title: strings.TrimSpace(feed.Title), SourceType: "rss"}, nil
		}
	}

	// Try RDF (<rdf:RDF>)
	if strings.Contains(peek, "<rdf:RDF") || strings.Contains(peek, "<RDF") {
		var feed struct {
			Channel struct {
				Title string `xml:"title"`
			} `xml:"channel"`
		}
		if err := xml.NewDecoder(bytes.NewReader(body)).Decode(&feed); err == nil && feed.Channel.Title != "" {
			return &FeedMeta{Title: strings.TrimSpace(feed.Channel.Title), SourceType: "rss"}, nil
		}
	}

	// Fallback: RSS 2.0 (<rss><channel>)
	var rssFeed struct {
		Channel struct {
			Title string `xml:"title"`
		} `xml:"channel"`
	}
	if err := xml.NewDecoder(bytes.NewReader(body)).Decode(&rssFeed); err == nil && rssFeed.Channel.Title != "" {
		return &FeedMeta{Title: strings.TrimSpace(rssFeed.Channel.Title), SourceType: "rss"}, nil
	}

	return nil, fmt.Errorf("cannot determine feed title from %s", url)
}

// --- Helpers ---

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
