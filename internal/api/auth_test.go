package api

import (
	"testing"
)

func TestWeChatCodeToOpenID_errors(t *testing.T) {
	tests := []struct {
		name   string
		appID  string
		code   string
		secret string
	}{
		{
			name:   "empty appID",
			appID:  "",
			code:   "valid-code",
			secret: "valid-secret",
		},
		{
			name:   "empty secret",
			appID:  "valid-appid",
			code:   "valid-code",
			secret: "",
		},
		{
			name:   "empty code",
			appID:  "valid-appid",
			code:   "",
			secret: "valid-secret",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := weChatCodeToOpenID(tt.appID, tt.code, tt.secret)
			if err == nil {
				t.Fatal("weChatCodeToOpenID() expected error, got nil")
			}
		})
	}
}
