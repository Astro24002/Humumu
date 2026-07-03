package api

import (
	"log"
	"net/http"
	"regexp"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/fetcher"
	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/repo"
)

type UserJournalHandler struct {
	journalRepo *repo.JournalRepo
	subRepo     *repo.SubscriptionRepo
}

func NewUserJournalHandler(journalRepo *repo.JournalRepo, subRepo *repo.SubscriptionRepo) *UserJournalHandler {
	return &UserJournalHandler{
		journalRepo: journalRepo,
		subRepo:     subRepo,
	}
}

type PreviewRequest struct {
	SourceURL string `json:"source_url" binding:"required,url"`
}

type PreviewResponse struct {
	Name       string `json:"name"`
	SourceType string `json:"source_type"`
}

func (h *UserJournalHandler) Preview(c *gin.Context) {
	var req PreviewRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "valid source_url is required"})
		return
	}

	meta, err := fetcher.FetchFeedMeta(c.Request.Context(), req.SourceURL)
	if err != nil {
		log.Printf("preview fetch error [%s]: %v", req.SourceURL, err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "cannot fetch feed from this URL"})
		return
	}

	c.JSON(http.StatusOK, PreviewResponse{
		Name:       meta.Title,
		SourceType: meta.SourceType,
	})
}

type CreateUserJournalRequest struct {
	SourceURL string `json:"source_url" binding:"required,url"`
	Name      string `json:"name" binding:"required"`
}

func (h *UserJournalHandler) Create(c *gin.Context) {
	userID := c.GetString("user_id")

	var req CreateUserJournalRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "name and source_url are required"})
		return
	}

	// Check if journal already exists for this URL
	existing, err := h.journalRepo.FindByURL(c.Request.Context(), req.SourceURL)
	if err != nil {
		log.Printf("error checking existing journal: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to check existing journal"})
		return
	}
	if existing != nil {
		// Journal exists — just subscribe and return it
		if err := h.subRepo.AddJournal(c.Request.Context(), userID, existing.ID); err != nil {
			log.Printf("error subscribing to existing journal: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to subscribe"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"journal": existing, "already_existed": true})
		return
	}

	// Generate slug from name
	slug := slugify(req.Name)

	// Create the journal
	journal := &model.Journal{
		Name:          req.Name,
		Slug:          slug,
		SourceType:    "rss",
		SourceURL:     req.SourceURL,
		Description:   "",
		FetchInterval: 30 * time.Minute,
		IsActive:      true,
		CreatedBy:     &userID,
	}

	if err := h.journalRepo.Create(c.Request.Context(), journal); err != nil {
		log.Printf("error creating journal: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create journal"})
		return
	}

	// Subscribe the user to the new journal
	if err := h.subRepo.AddJournal(c.Request.Context(), userID, journal.ID); err != nil {
		log.Printf("error subscribing to new journal: %v", err)
		// Journal created but subscribe failed — still return success?
		c.JSON(http.StatusInternalServerError, gin.H{"error": "journal created but subscription failed"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"journal": journal, "already_existed": false})
}

// slugify converts a name into a URL-friendly slug.
func slugify(name string) string {
	s := strings.ToLower(name)
	// Replace non-alphanumeric characters (except hyphens and spaces) with nothing
	re := regexp.MustCompile(`[^a-z0-9一-鿿\s-]`)
	s = re.ReplaceAllString(s, "")
	// Replace spaces with hyphens
	s = strings.ReplaceAll(s, " ", "-")
	// Collapse multiple hyphens
	re2 := regexp.MustCompile(`-+`)
	s = re2.ReplaceAllString(s, "-")
	// Trim leading/trailing hyphens
	s = strings.Trim(s, "-")
	if s == "" {
		s = "journal"
	}
	return s
}
