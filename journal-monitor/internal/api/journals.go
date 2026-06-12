package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/repo"
)

type JournalHandler struct {
	journalRepo *repo.JournalRepo
}

func NewJournalHandler(journalRepo *repo.JournalRepo) *JournalHandler {
	return &JournalHandler{journalRepo: journalRepo}
}

func (h *JournalHandler) List(c *gin.Context) {
	journals, err := h.journalRepo.GetAll(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch journals"})
		return
	}
	if journals == nil {
		journals = []*model.Journal{}
	}
	c.JSON(http.StatusOK, gin.H{"journals": journals})
}

func (h *JournalHandler) Get(c *gin.Context) {
	id := c.Param("id")
	journal, err := h.journalRepo.GetByID(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch journal"})
		return
	}
	if journal == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "journal not found"})
		return
	}
	c.JSON(http.StatusOK, journal)
}
