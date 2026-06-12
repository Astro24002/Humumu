package matcher

import (
	"context"
	"strings"

	"github.com/humumu/journal-monitor/internal/model"
)

func (e *Engine) matchAuthors(ctx context.Context, article *model.Article) ([]MatchResult, error) {
	if len(article.Authors) == 0 {
		return nil, nil
	}

	trackedAuthors, err := e.subRepo.GetAllTrackedAuthors(ctx)
	if err != nil {
		return nil, err
	}

	var results []MatchResult
	for _, ta := range trackedAuthors {
		for _, author := range article.Authors {
			if strings.EqualFold(strings.TrimSpace(author), strings.TrimSpace(ta.AuthorName)) {
				results = append(results, MatchResult{
					UserID:    ta.UserID,
					ArticleID: article.ID,
				})
				break
			}
		}
	}
	return results, nil
}
