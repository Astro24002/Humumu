package cache

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

type DedupCache struct {
	client *redis.Client
	ttl    time.Duration
}

func NewDedupCache(client *redis.Client) *DedupCache {
	return &DedupCache{
		client: client,
		ttl:    7 * 24 * time.Hour,
	}
}

func (d *DedupCache) IsDuplicate(ctx context.Context, journalID, doi string) (bool, error) {
	if doi == "" {
		return false, nil
	}
	key := fmt.Sprintf("dedup:%s:%s", journalID, doi)
	exists, err := d.client.Exists(ctx, key).Result()
	if err != nil {
		return false, err
	}
	if exists > 0 {
		return true, nil
	}
	return false, d.client.Set(ctx, key, "1", d.ttl).Err()
}

func (d *DedupCache) MarkSeen(ctx context.Context, journalID, doi string) error {
	if doi == "" {
		return nil
	}
	key := fmt.Sprintf("dedup:%s:%s", journalID, doi)
	return d.client.Set(ctx, key, "1", d.ttl).Err()
}

func (d *DedupCache) SeedFromDB(ctx context.Context, journalID string, dois []string) error {
	pipe := d.client.Pipeline()
	for _, doi := range dois {
		key := fmt.Sprintf("dedup:%s:%s", journalID, doi)
		pipe.Set(ctx, key, "1", d.ttl)
	}
	_, err := pipe.Exec(ctx)
	return err
}
