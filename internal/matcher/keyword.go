package matcher

import (
	"context"
	"strings"

	"github.com/humumu/journal-monitor/internal/model"
)

func (e *Engine) matchKeywords(ctx context.Context, article *model.Article) ([]MatchResult, error) {
	if article.Title == "" && article.Abstract == "" {
		return nil, nil
	}

	keywords, err := e.subRepo.GetAllKeywords(ctx)
	if err != nil {
		return nil, err
	}

	titleLower := strings.ToLower(article.Title)
	abstractLower := strings.ToLower(article.Abstract)

	var results []MatchResult
	for _, ks := range keywords {
		kwLower := strings.ToLower(ks.Keyword)
		if strings.Contains(titleLower, kwLower) || strings.Contains(abstractLower, kwLower) {
			results = append(results, MatchResult{
				UserID:    ks.UserID,
				ArticleID: article.ID,
			})
		}
	}
	return results, nil
}
