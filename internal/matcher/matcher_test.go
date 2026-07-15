package matcher

import (
	"testing"
)

func TestDedupResults(t *testing.T) {
	tests := []struct {
		name string
		in   []MatchResult
		want int
	}{
		{
			name: "empty",
			in:   nil,
			want: 0,
		},
		{
			name: "no duplicates",
			in: []MatchResult{
				{UserID: "u1", ArticleID: "a1"},
				{UserID: "u2", ArticleID: "a2"},
			},
			want: 2,
		},
		{
			name: "same user same article",
			in: []MatchResult{
				{UserID: "u1", ArticleID: "a1"},
				{UserID: "u1", ArticleID: "a1"},
			},
			want: 1,
		},
		{
			name: "same user different articles kept",
			in: []MatchResult{
				{UserID: "u1", ArticleID: "a1"},
				{UserID: "u1", ArticleID: "a2"},
			},
			want: 2,
		},
		{
			name: "same article different users kept",
			in: []MatchResult{
				{UserID: "u1", ArticleID: "a1"},
				{UserID: "u2", ArticleID: "a1"},
			},
			want: 2,
		},
		{
			name: "mixed duplicates",
			in: []MatchResult{
				{UserID: "u1", ArticleID: "a1"},
				{UserID: "u1", ArticleID: "a2"},
				{UserID: "u2", ArticleID: "a1"},
				{UserID: "u1", ArticleID: "a1"},
				{UserID: "u3", ArticleID: "a3"},
				{UserID: "u2", ArticleID: "a1"},
			},
			want: 4,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := dedupResults(tt.in)
			if len(got) != tt.want {
				t.Errorf("dedupResults() returned %d items, want %d", len(got), tt.want)
			}
		})
	}
}
