package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/repo"
)

type SubscriptionHandler struct {
	subRepo     *repo.SubscriptionRepo
	journalRepo *repo.JournalRepo
}

func NewSubscriptionHandler(subRepo *repo.SubscriptionRepo, journalRepo *repo.JournalRepo) *SubscriptionHandler {
	return &SubscriptionHandler{subRepo: subRepo, journalRepo: journalRepo}
}

// Journal subscriptions

func (h *SubscriptionHandler) ListJournals(c *gin.Context) {
	userID := c.GetString("user_id")
	journals, err := h.subRepo.GetUserJournals(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch subscriptions"})
		return
	}
	if journals == nil {
		journals = []*model.Journal{}
	}
	c.JSON(http.StatusOK, gin.H{"journals": journals})
}

func (h *SubscriptionHandler) SubscribeJournal(c *gin.Context) {
	userID := c.GetString("user_id")
	journalID := c.Param("id")

	journal, err := h.journalRepo.GetByID(c.Request.Context(), journalID)
	if err != nil || journal == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "journal not found"})
		return
	}
	if err := h.subRepo.AddJournal(c.Request.Context(), userID, journalID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to subscribe"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "subscribed"})
}

func (h *SubscriptionHandler) UnsubscribeJournal(c *gin.Context) {
	userID := c.GetString("user_id")
	journalID := c.Param("id")
	if err := h.subRepo.RemoveJournal(c.Request.Context(), userID, journalID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to unsubscribe"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "unsubscribed"})
}

// Author tracking

func (h *SubscriptionHandler) ListAuthors(c *gin.Context) {
	userID := c.GetString("user_id")
	authors, err := h.subRepo.GetUserAuthors(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch authors"})
		return
	}
	if authors == nil {
		authors = []*model.AuthorTracking{}
	}
	c.JSON(http.StatusOK, gin.H{"authors": authors})
}

func (h *SubscriptionHandler) AddAuthor(c *gin.Context) {
	userID := c.GetString("user_id")
	var req model.AuthorTrackingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.subRepo.AddAuthor(c.Request.Context(), userID, req.AuthorName); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to add author"})
		return
	}
	c.JSON(http.StatusCreated, gin.H{"message": "author added"})
}

func (h *SubscriptionHandler) RemoveAuthor(c *gin.Context) {
	userID := c.GetString("user_id")
	id := c.Param("id")
	if err := h.subRepo.RemoveAuthor(c.Request.Context(), id, userID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to remove author"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "author removed"})
}

// Keyword subscriptions

func (h *SubscriptionHandler) ListKeywords(c *gin.Context) {
	userID := c.GetString("user_id")
	keywords, err := h.subRepo.GetUserKeywords(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch keywords"})
		return
	}
	if keywords == nil {
		keywords = []*model.KeywordSubscription{}
	}
	c.JSON(http.StatusOK, gin.H{"keywords": keywords})
}

func (h *SubscriptionHandler) AddKeyword(c *gin.Context) {
	userID := c.GetString("user_id")
	var req model.KeywordSubscriptionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.subRepo.AddKeyword(c.Request.Context(), userID, req.Keyword); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to add keyword"})
		return
	}
	c.JSON(http.StatusCreated, gin.H{"message": "keyword added"})
}

func (h *SubscriptionHandler) RemoveKeyword(c *gin.Context) {
	userID := c.GetString("user_id")
	id := c.Param("id")
	if err := h.subRepo.RemoveKeyword(c.Request.Context(), id, userID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to remove keyword"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "keyword removed"})
}
