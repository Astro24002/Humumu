package config

import (
	"os"
	"testing"
)

func TestGetEnv(t *testing.T) {
	const key = "TEST_GETENV_KEY"
	os.Unsetenv(key)

	t.Run("fallback when unset", func(t *testing.T) {
		got := getEnv(key, "default")
		if got != "default" {
			t.Errorf("getEnv() = %q, want %q", got, "default")
		}
	})

	t.Run("returns env value when set", func(t *testing.T) {
		os.Setenv(key, "env_value")
		defer os.Unsetenv(key)
		got := getEnv(key, "default")
		if got != "env_value" {
			t.Errorf("getEnv() = %q, want %q", got, "env_value")
		}
	})
}

func TestGetEnvInt(t *testing.T) {
	const key = "TEST_GETENVINT_KEY"
	os.Unsetenv(key)

	t.Run("fallback when unset", func(t *testing.T) {
		got := getEnvInt(key, 42)
		if got != 42 {
			t.Errorf("getEnvInt() = %d, want %d", got, 42)
		}
	})

	t.Run("returns int value when set", func(t *testing.T) {
		os.Setenv(key, "99")
		defer os.Unsetenv(key)
		got := getEnvInt(key, 42)
		if got != 99 {
			t.Errorf("getEnvInt() = %d, want %d", got, 99)
		}
	})

	t.Run("fallback on invalid int", func(t *testing.T) {
		os.Setenv(key, "not-a-number")
		defer os.Unsetenv(key)
		got := getEnvInt(key, 7)
		if got != 7 {
			t.Errorf("getEnvInt() = %d, want %d", got, 7)
		}
	})
}

func TestValidate(t *testing.T) {
	t.Run("rejects empty JWT secret", func(t *testing.T) {
		cfg := &Config{}
		err := cfg.Validate()
		if err == nil {
			t.Fatal("Validate() expected error, got nil")
		}
	})

	t.Run("accepts non-empty JWT secret", func(t *testing.T) {
		cfg := &Config{JWT: JWTConfig{Secret: "my-secret"}}
		err := cfg.Validate()
		if err != nil {
			t.Fatalf("Validate() unexpected error: %v", err)
		}
	})
}
