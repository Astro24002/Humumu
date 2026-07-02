package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/repo"
)

type WeChatHandler struct {
	userRepo *repo.UserRepo
}

func NewWeChatHandler(userRepo *repo.UserRepo) *WeChatHandler {
	return &WeChatHandler{userRepo: userRepo}
}

type UpdateTemplateSettingRequest struct {
	Subscribed bool `json:"subscribed" binding:"required"`
}

func (h *WeChatHandler) GetTemplateSetting(c *gin.Context) {
	userID := c.GetString("user_id")
	subscribed, err := h.userRepo.GetTemplateSetting(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "server error"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"subscribed": subscribed})
}

func (h *WeChatHandler) UpdateTemplateSetting(c *gin.Context) {
	userID := c.GetString("user_id")
	var req UpdateTemplateSettingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.userRepo.UpdateTemplateSetting(c.Request.Context(), userID, req.Subscribed); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "server error"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"subscribed": req.Subscribed})
}
