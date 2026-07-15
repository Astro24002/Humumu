package notifier

import (
	"testing"

	"github.com/humumu/journal-monitor/internal/model"
)

func TestTruncate(t *testing.T) {
	tests := []struct {
		name   string
		input  string
		maxLen int
		want   string
	}{
		{
			name:   "short string kept as-is",
			input:  "hello",
			maxLen: 10,
			want:   "hello",
		},
		{
			name:   "exact length kept",
			input:  "12345",
			maxLen: 5,
			want:   "12345",
		},
		{
			name:   "long string truncated",
			input:  "hello world this is long",
			maxLen: 10,
			want:   "hello w...",
		},
		{
			name:   "empty string",
			input:  "",
			maxLen: 10,
			want:   "",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := truncate(tt.input, tt.maxLen)
			if got != tt.want {
				t.Errorf("truncate() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestRenderEmail(t *testing.T) {
	n := &EmailNotifier{}

	article := &model.ArticleWithJournal{
		JournalName: "Test Journal",
		Article: model.Article{
			Title:   "Test Article",
			Authors: []string{"Alice", "Bob"},
			Abstract: "This is a test abstract.",
			DOI:     "10.1234/test",
			URL:     "https://example.com/article",
		},
	}

	html, err := n.renderEmail(article)
	if err != nil {
		t.Fatalf("renderEmail() error: %v", err)
	}

	checks := []string{
		"Test Journal",
		"Test Article",
		"Alice, Bob",
		"This is a test abstract.",
		"10.1234/test",
		"https://example.com/article",
	}
	for _, c := range checks {
		if !contains(html, c) {
			t.Errorf("renderEmail() output missing: %s", c)
		}
	}
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && searchString(s, substr)
}

func searchString(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
