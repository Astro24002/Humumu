package notifier

import (
	"bytes"
	"context"
	"fmt"
	"html/template"
	"log"
	"net/smtp"
	"strings"

	"github.com/humumu/journal-monitor/internal/config"
	"github.com/humumu/journal-monitor/internal/model"
)

type EmailNotifier struct {
	cfg config.SMTPConfig
}

func NewEmailNotifier(cfg config.SMTPConfig) *EmailNotifier {
	return &EmailNotifier{cfg: cfg}
}

func (n *EmailNotifier) Name() string { return "email" }

func (n *EmailNotifier) Send(ctx context.Context, user *model.User, article *model.ArticleWithJournal) error {
	if user.Email == "" || n.cfg.Host == "" {
		return fmt.Errorf("email not configured or user has no email")
	}

	subject := fmt.Sprintf("[%s] %s", article.JournalName, truncate(article.Title, 80))
	body, err := n.renderEmail(article)
	if err != nil {
		return fmt.Errorf("render email: %w", err)
	}

	msg := fmt.Sprintf("From: %s\r\nTo: %s\r\nSubject: %s\r\nMIME-Version: 1.0\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n%s",
		n.cfg.From, user.Email, subject, body)

	auth := smtp.PlainAuth("", n.cfg.User, n.cfg.Password, n.cfg.Host)
	addr := fmt.Sprintf("%s:%d", n.cfg.Host, n.cfg.Port)

	if err := smtp.SendMail(addr, auth, n.cfg.From, []string{user.Email}, []byte(msg)); err != nil {
		return fmt.Errorf("send email: %w", err)
	}

	log.Printf("email sent to %s for article %s", user.Email, article.DOI)
	return nil
}

const emailTemplate = `
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #2c3e50;">{{.JournalName}}</h2>
    <h3>{{.Title}}</h3>
    <p style="color: #7f8c8d;">{{.AuthorsDisplay}}</p>
    <hr>
    <p>{{.Abstract}}</p>
    <p>
        <a href="{{.URL}}" style="background: #3498db; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">Read Full Article</a>
        &nbsp; DOI: {{.DOI}}
    </p>
</body>
</html>`

type emailData struct {
	model.ArticleWithJournal
	AuthorsDisplay string
}

func (n *EmailNotifier) renderEmail(article *model.ArticleWithJournal) (string, error) {
	tmpl, err := template.New("email").Parse(emailTemplate)
	if err != nil {
		return "", err
	}

	data := emailData{
		ArticleWithJournal: *article,
		AuthorsDisplay:     strings.Join(article.Authors, ", "),
	}

	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, data); err != nil {
		return "", err
	}
	return buf.String(), nil
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}
