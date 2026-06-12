// internal/api/auth.go
package api

import (
	"errors"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/humumu/journal-monitor/internal/config"
	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/repo"
	"golang.org/x/crypto/bcrypt"
)

type AuthHandler struct {
	userRepo  *repo.UserRepo
	jwtCfg    config.JWTConfig
	weChatCfg config.WeChatConfig
}

func NewAuthHandler(userRepo *repo.UserRepo, jwtCfg config.JWTConfig, weChatCfg config.WeChatConfig) *AuthHandler {
	return &AuthHandler{userRepo: userRepo, jwtCfg: jwtCfg, weChatCfg: weChatCfg}
}

type Claims struct {
	UserID string `json:"user_id"`
	Email  string `json:"email"`
	jwt.RegisteredClaims
}

func (h *AuthHandler) Register(c *gin.Context) {
	var req model.RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	existing, err := h.userRepo.GetByEmail(c.Request.Context(), req.Email)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "server error"})
		return
	}
	if existing != nil {
		c.JSON(http.StatusConflict, gin.H{"error": "email already registered"})
		return
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to hash password"})
		return
	}

	user := &model.User{
		Email:         req.Email,
		PasswordHash:  string(hash),
		Name:          req.Name,
		PushFrequency: "realtime",
	}
	if err := h.userRepo.Create(c.Request.Context(), user); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create user"})
		return
	}

	token, err := h.generateToken(user.ID, user.Email)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to generate token"})
		return
	}

	c.JSON(http.StatusCreated, model.AuthResponse{Token: token, User: *user})
}

func (h *AuthHandler) Login(c *gin.Context) {
	var req model.LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	user, err := h.userRepo.GetByEmail(c.Request.Context(), req.Email)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "server error"})
		return
	}
	if user == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid email or password"})
		return
	}

	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(req.Password)); err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid email or password"})
		return
	}

	token, err := h.generateToken(user.ID, user.Email)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to generate token"})
		return
	}

	c.JSON(http.StatusOK, model.AuthResponse{Token: token, User: *user})
}

func (h *AuthHandler) WeChatLogin(c *gin.Context) {
	var req model.WeChatLoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Call WeChat API with code to get openid
	openID, err := weChatCodeToOpenID(req.Code, h.weChatCfg.Secret)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "wechat login failed"})
		return
	}

	user, err := h.userRepo.GetByWeChatOpenID(c.Request.Context(), openID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "server error"})
		return
	}

	if user == nil {
		// New user via WeChat — create a stub account
		user = &model.User{
			Email:         openID + "@wechat.user", // placeholder, editable later
			PasswordHash:  "",
			Name:          "WeChat User",
			WeChatOpenID:  openID,
			PushFrequency: "realtime",
		}
		if err := h.userRepo.Create(c.Request.Context(), user); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create user"})
			return
		}
	}

	token, err := h.generateToken(user.ID, user.Email)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to generate token"})
		return
	}

	c.JSON(http.StatusOK, model.AuthResponse{Token: token, User: *user})
}

// weChatCodeToOpenID calls the WeChat API to exchange a login code for an openid.
// For MVP, returns a placeholder; replace with actual HTTP call when WeChat credentials are set.
func weChatCodeToOpenID(code, secret string) (string, error) {
	if code == "" {
		return "", errors.New("empty code")
	}
	// TODO: actual HTTP call to https://api.weixin.qq.com/sns/jscode2session
	// WeChat API returns: { openid, session_key, unionid }
	// For now, use code as a stand-in to allow development without WeChat credentials
	return "mock_openid_" + code, nil
}

func (h *AuthHandler) generateToken(userID, email string) (string, error) {
	claims := &Claims{
		UserID: userID,
		Email:  email,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(72 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(h.jwtCfg.Secret))
}
