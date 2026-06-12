package fetcher

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/humumu/journal-monitor/internal/model"
)

type FetchResult struct {
	JournalID   string
	JournalName string
	Articles    []RawArticle
	Err         error
	Duration    time.Duration
}

type Manager struct {
	sources map[string]Source
	mu      sync.RWMutex
}

func NewManager() *Manager {
	return &Manager{
		sources: make(map[string]Source),
	}
}

func (m *Manager) Register(journalID string, source Source) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.sources[journalID] = source
}

func (m *Manager) FetchAll(ctx context.Context, journals []*model.Journal) []FetchResult {
	var results []FetchResult
	var mu sync.Mutex
	var wg sync.WaitGroup

	for _, j := range journals {
		if !j.IsActive {
			continue
		}
		wg.Add(1)
		go func(j *model.Journal) {
			defer wg.Done()
			result := m.fetchOne(ctx, j)
			mu.Lock()
			results = append(results, result)
			mu.Unlock()
		}(j)
	}

	wg.Wait()
	return results
}

func (m *Manager) fetchOne(ctx context.Context, j *model.Journal) FetchResult {
	start := time.Now()

	m.mu.RLock()
	source, ok := m.sources[j.ID]
	m.mu.RUnlock()

	if !ok {
		source = m.createSource(j)
		if source == nil {
			return FetchResult{
				JournalID:   j.ID,
				JournalName: j.Name,
				Err:         ErrUnsupportedSource,
			}
		}
		m.Register(j.ID, source)
	}

	fetchCtx, cancel := context.WithTimeout(ctx, 60*time.Second)
	defer cancel()

	articles, err := source.Fetch(fetchCtx)
	duration := time.Since(start)

	if err != nil {
		log.Printf("fetch error [%s]: %v", j.Name, err)
	}

	return FetchResult{
		JournalID:   j.ID,
		JournalName: j.Name,
		Articles:    articles,
		Err:         err,
		Duration:    duration,
	}
}

func (m *Manager) createSource(j *model.Journal) Source {
	switch j.SourceType {
	case "rss":
		return NewRSSSource(j.Name, j.SourceURL)
	case "arxiv":
		return NewArxivSource(j.Name, j.SourceURL)
	default:
		return nil
	}
}

var ErrUnsupportedSource = fmt.Errorf("unsupported source type")
