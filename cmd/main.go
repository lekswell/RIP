package main

import (
	"async-service/internal/api"
	"fmt"
	"log"

	"github.com/gin-gonic/gin"
)

func main() {
	router := gin.Default()
	router.POST("/Async/", api.AsyncService)

	fmt.Println("Starting server on :8080...")
	err := router.Run(":8080")
	if err != nil {
		log.Fatal(err)
	}
}
