package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/repo"
)

type RequestHandler struct {
	journalRepo *repo.JournalRepo
}

func NewRequestHandler(journalRepo *repo.JournalRepo) *RequestHandler {
	return &RequestHandler{journalRepo: journalRepo}
}

func (h *RequestHandler) Create(c *gin.Context) {
	userID := c.GetString("user_id")
	var req model.CreateJournalRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	jr := &model.JournalRequest{
		UserID:      userID,
		JournalName: req.JournalName,
		SourceURL:   req.SourceURL,
		Status:      "pending",
	}
	if err := h.journalRepo.CreateRequest(c.Request.Context(), jr); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create request"})
		return
	}
	c.JSON(http.StatusCreated, jr)
}

func (h *RequestHandler) List(c *gin.Context) {
	userID := c.GetString("user_id")
	reqs, err := h.journalRepo.GetRequestsByUser(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch requests"})
		return
	}
	if reqs == nil {
		reqs = []*model.JournalRequest{}
	}
	c.JSON(http.StatusOK, gin.H{"requests": reqs})
}
