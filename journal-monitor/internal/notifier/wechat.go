package notifier

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/humumu/journal-monitor/internal/config"
	"github.com/humumu/journal-monitor/internal/model"
)

type WeChatNotifier struct {
	cfg    config.WeChatConfig
	client *http.Client
}

func NewWeChatNotifier(cfg config.WeChatConfig) *WeChatNotifier {
	return &WeChatNotifier{
		cfg:    cfg,
		client: &http.Client{Timeout: 10 * time.Second},
	}
}

func (n *WeChatNotifier) Name() string { return "wechat" }

func (n *WeChatNotifier) Send(ctx context.Context, user *model.User, article *model.ArticleWithJournal) error {
	if user.WeChatOpenID == "" || n.cfg.AppID == "" {
		return fmt.Errorf("wechat not configured or user has no wechat openid")
	}

	token, err := n.getAccessToken(ctx)
	if err != nil {
		return fmt.Errorf("get access token: %w", err)
	}

	type wechatTemplateMsg struct {
		ToUser     string `json:"touser"`
		TemplateID string `json:"template_id"`
		Data       map[string]struct {
			Value string `json:"value"`
			Color string `json:"color"`
		} `json:"data"`
	}

	msg := wechatTemplateMsg{
		ToUser:     user.WeChatOpenID,
		TemplateID: "",
		Data: map[string]struct {
			Value string `json:"value"`
			Color string `json:"color"`
		}{
			"journal":  {Value: article.JournalName, Color: "#2c3e50"},
			"title":    {Value: truncate(article.Title, 100), Color: "#000000"},
			"authors":  {Value: truncate(strings.Join(article.Authors, ", "), 80), Color: "#7f8c8d"},
			"abstract": {Value: truncate(article.Abstract, 200), Color: "#666666"},
			"doi":      {Value: article.DOI, Color: "#3498db"},
		},
	}

	body, _ := json.Marshal(msg)
	url := fmt.Sprintf("https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token=%s", token)

	resp, err := n.client.Post(url, "application/json", bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("wechat api request: %w", err)
	}
	defer resp.Body.Close()

	var result struct {
		Errcode int    `json:"errcode"`
		Errmsg  string `json:"errmsg"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return fmt.Errorf("wechat decode: %w", err)
	}

	if result.Errcode != 0 {
		return fmt.Errorf("wechat api error: %d %s", result.Errcode, result.Errmsg)
	}

	log.Printf("wechat message sent to %s for article %s", user.WeChatOpenID, article.DOI)
	return nil
}

type accessTokenResponse struct {
	AccessToken string `json:"access_token"`
	ExpiresIn   int    `json:"expires_in"`
}

func (n *WeChatNotifier) getAccessToken(ctx context.Context) (string, error) {
	url := fmt.Sprintf("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s",
		n.cfg.AppID, n.cfg.Secret)

	resp, err := n.client.Get(url)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result accessTokenResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}

	if result.AccessToken == "" {
		return "", fmt.Errorf("failed to get wechat access token")
	}

	return result.AccessToken, nil
}
