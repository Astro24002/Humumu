package api

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/repo"
)

type NotificationHandler struct {
	notifRepo *repo.NotificationRepo
}

func NewNotificationHandler(notifRepo *repo.NotificationRepo) *NotificationHandler {
	return &NotificationHandler{notifRepo: notifRepo}
}

func (h *NotificationHandler) List(c *gin.Context) {
	userID := c.GetString("user_id")
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	if limit > 100 {
		limit = 100
	}
	notifs, err := h.notifRepo.GetByUser(c.Request.Context(), userID, limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch notifications"})
		return
	}
	if notifs == nil {
		notifs = []*model.Notification{}
	}
	c.JSON(http.StatusOK, gin.H{"notifications": notifs})
}
