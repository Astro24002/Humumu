package api

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/repo"
)

type ArticleHandler struct {
	articleRepo *repo.ArticleRepo
}

func NewArticleHandler(articleRepo *repo.ArticleRepo) *ArticleHandler {
	return &ArticleHandler{articleRepo: articleRepo}
}

func (h *ArticleHandler) List(c *gin.Context) {
	userID := c.GetString("user_id")
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	if limit > 100 {
		limit = 100
	}

	journalID := c.Query("journal_id")
	var articles []*model.Article
	var err error

	if journalID != "" {
		articles, err = h.articleRepo.GetByJournal(c.Request.Context(), journalID, limit, offset)
	} else {
		articles, err = h.articleRepo.GetByUserSubscriptions(c.Request.Context(), userID, limit, offset)
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch articles"})
		return
	}
	if articles == nil {
		articles = []*model.Article{}
	}
	c.JSON(http.StatusOK, gin.H{"articles": articles})
}

func (h *ArticleHandler) Get(c *gin.Context) {
	id := c.Param("id")
	article, err := h.articleRepo.GetByID(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch article"})
		return
	}
	if article == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "article not found"})
		return
	}
	c.JSON(http.StatusOK, article)
}

func (h *ArticleHandler) MyFeed(c *gin.Context) {
	userID := c.GetString("user_id")
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	if limit > 100 {
		limit = 100
	}

	articles, err := h.articleRepo.GetByUserSubscriptions(c.Request.Context(), userID, limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch articles"})
		return
	}
	if articles == nil {
		articles = []*model.Article{}
	}
	c.JSON(http.StatusOK, gin.H{"articles": articles})
}
