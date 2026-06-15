package main

import (
	"log"
	"net/http"
	"os"
	"path/filepath"
)

// SPAFiles returns an http.FileSystem for serving the built SPA from disk.
// In development, Vite runs on :5173 with a proxy — so this is only used
// in production (Docker / make build) where web/dist/ is deployed alongside the binary.
func SPAFiles() http.FileSystem {
	abs, err := filepath.Abs("web/dist")
	if err != nil {
		log.Printf("warning: SPA dist not found: %v", err)
		return http.FS(os.DirFS("/dev/null"))
	}
	if _, err := os.Stat(abs); os.IsNotExist(err) {
		log.Printf("warning: no SPA dist found at %s — running API-only mode", abs)
		return http.FS(os.DirFS("/dev/null"))
	}
	log.Printf("serving SPA from %s", abs)
	return http.FS(os.DirFS(abs))
}
