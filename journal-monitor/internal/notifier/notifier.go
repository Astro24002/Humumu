package notifier

import (
	"context"

	"github.com/humumu/journal-monitor/internal/model"
)

type Notifier interface {
	Name() string
	Send(ctx context.Context, user *model.User, article *model.ArticleWithJournal) error
}
