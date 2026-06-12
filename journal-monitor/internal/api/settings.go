package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/repo"
)

type SettingsHandler struct {
	userRepo *repo.UserRepo
}

func NewSettingsHandler(userRepo *repo.UserRepo) *SettingsHandler {
	return &SettingsHandler{userRepo: userRepo}
}

func (h *SettingsHandler) UpdatePushFrequency(c *gin.Context) {
	userID := c.GetString("user_id")
	var req model.UpdatePushFrequencyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.userRepo.UpdatePushFrequency(c.Request.Context(), userID, req.PushFrequency); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update settings"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "settings updated"})
}
