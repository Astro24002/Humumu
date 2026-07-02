package config

import (
	"fmt"
	"log"
	"os"
	"strconv"
	"time"
)

type Config struct {
	Server   ServerConfig
	DB       DBConfig
	Redis    RedisConfig
	SMTP     SMTPConfig
	WeChat   WeChatConfig
	JWT      JWTConfig
	Fetch    FetchConfig
}

type ServerConfig struct {
	Port string
}

type DBConfig struct {
	DSN string
}

type RedisConfig struct {
	Addr string
}

type SMTPConfig struct {
	Host     string
	Port     int
	User     string
	Password string
	From     string
}

type WeChatConfig struct {
	AppID              string
	Secret             string
	TemplateIDRealtime string // subscribe message template for realtime
	TemplateIDDaily    string // subscribe message template for daily summary
}

type JWTConfig struct {
	Secret string
}

type FetchConfig struct {
	DefaultInterval time.Duration
}

func Load() *Config {
	return &Config{
		Server: ServerConfig{
			Port: getEnv("SERVER_PORT", "8080"),
		},
		DB: DBConfig{
			DSN: getEnv("DB_DSN", "postgres://postgres:postgres@localhost:5432/journal_monitor?sslmode=disable"),
		},
		Redis: RedisConfig{
			Addr: getEnv("REDIS_ADDR", "localhost:6379"),
		},
		SMTP: SMTPConfig{
			Host:     getEnv("SMTP_HOST", ""),
			Port:     getEnvInt("SMTP_PORT", 587),
			User:     getEnv("SMTP_USER", ""),
			Password: getEnv("SMTP_PASS", ""),
			From:     getEnv("SMTP_FROM", ""),
		},
		WeChat: WeChatConfig{
			AppID:              getEnv("WECHAT_APPID", ""),
			Secret:             getEnv("WECHAT_SECRET", ""),
			TemplateIDRealtime: getEnv("WECHAT_TEMPLATE_REALTIME", ""),
			TemplateIDDaily:    getEnv("WECHAT_TEMPLATE_DAILY", ""),
		},
		JWT: JWTConfig{
			Secret: getEnv("JWT_SECRET", "change-me-to-something-secure"),
		},
		Fetch: FetchConfig{
			DefaultInterval: getEnvDuration("FETCH_INTERVAL_MINUTES", 30),
		},
	}
}

func (c *Config) Validate() error {
	if c.JWT.Secret == "" {
		return fmt.Errorf("JWT_SECRET must not be empty")
	}
	return nil
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
		log.Printf("warning: invalid value for %s (expected integer, got %q), using default %d", key, v, fallback)
	}
	return fallback
}

func getEnvDuration(key string, fallbackMinutes int) time.Duration {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return time.Duration(i) * time.Minute
		}
		log.Printf("warning: invalid value for %s (expected integer, got %q), using default %d minutes", key, v, fallbackMinutes)
	}
	return time.Duration(fallbackMinutes) * time.Minute
}
