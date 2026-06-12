package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/repo"
)

type AdminHandler struct {
	journalRepo *repo.JournalRepo
	userRepo    *repo.UserRepo
	articleRepo *repo.ArticleRepo
}

func NewAdminHandler(journalRepo *repo.JournalRepo, userRepo *repo.UserRepo, articleRepo *repo.ArticleRepo) *AdminHandler {
	return &AdminHandler{
		journalRepo: journalRepo,
		userRepo:    userRepo,
		articleRepo: articleRepo,
	}
}

type AdminStatsResponse struct {
	JournalCount    int `json:"journal_count"`
	ArticleCount    int `json:"article_count"`
	UserCount       int `json:"user_count"`
	PendingRequests int `json:"pending_requests"`
}

func (h *AdminHandler) Stats(c *gin.Context) {
	journals, _ := h.journalRepo.GetAll(c.Request.Context())
	articles, _ := h.articleRepo.CountAll(c.Request.Context())
	users, _ := h.userRepo.GetAll(c.Request.Context())
	pending, _ := h.journalRepo.CountPendingRequests(c.Request.Context())

	c.JSON(http.StatusOK, AdminStatsResponse{
		JournalCount:    len(journals),
		ArticleCount:    articles,
		UserCount:       len(users),
		PendingRequests: pending,
	})
}

func (h *AdminHandler) ListJournals(c *gin.Context) {
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

func (h *AdminHandler) CreateJournal(c *gin.Context) {
	var j model.Journal
	if err := c.ShouldBindJSON(&j); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.journalRepo.Create(c.Request.Context(), &j); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create journal"})
		return
	}
	c.JSON(http.StatusCreated, j)
}

func (h *AdminHandler) UpdateJournal(c *gin.Context) {
	id := c.Param("id")
	var j model.Journal
	if err := c.ShouldBindJSON(&j); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.journalRepo.Update(c.Request.Context(), id, &j); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update journal"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "updated"})
}

func (h *AdminHandler) DeleteJournal(c *gin.Context) {
	id := c.Param("id")
	if err := h.journalRepo.Delete(c.Request.Context(), id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to delete journal"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "deleted"})
}

func (h *AdminHandler) ListRequests(c *gin.Context) {
	reqs, err := h.journalRepo.GetAllRequests(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch requests"})
		return
	}
	if reqs == nil {
		reqs = []*model.JournalRequest{}
	}
	c.JSON(http.StatusOK, gin.H{"requests": reqs})
}

type ReviewRequest struct {
	Status string `json:"status" binding:"required,oneof=approved rejected"`
}

func (h *AdminHandler) ReviewRequest(c *gin.Context) {
	id := c.Param("id")
	var req ReviewRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.journalRepo.UpdateRequestStatus(c.Request.Context(), id, req.Status); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update request"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "request " + req.Status})
}

func (h *AdminHandler) ListUsers(c *gin.Context) {
	users, err := h.userRepo.GetAll(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch users"})
		return
	}
	if users == nil {
		users = []*model.User{}
	}
	c.JSON(http.StatusOK, gin.H{"users": users})
}
