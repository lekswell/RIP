package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math/rand"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

type RequestData struct {
	Pk  int    `json:"pk"`
	Key string `json:"key"`
}

type PutData struct {
	Result bool `json:"result"`
	Pk     int  `json:"pk"`
}

func AsyncService(c *gin.Context) {
	if c.Request.Method != http.MethodPost {
		c.AbortWithStatusJSON(http.StatusMethodNotAllowed, gin.H{"error": "Метод не доступен"})
		return
	}

	var requestData RequestData
	if err := c.ShouldBindJSON(&requestData); err != nil {
		c.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}
	fmt.Printf("Received RequestData: %+v\n", requestData)
	if !validateKey(requestData.Key) {
		c.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"error": "Неправильный ключ"})
		return
	}

	// Запуск асинхронной функции для выполнения PUT-запроса
	go processPutRequest(requestData)

	// Возвращаем успешный ответ для POST-запроса
	c.JSON(http.StatusNoContent, nil)
}

func processPutRequest(requestData RequestData) {
	result := generateRandomBool()

	putData := PutData{
		Pk:     requestData.Pk,
		Result: result,
	}

	// Сериализация структуры в JSON
	jsonData, err := json.Marshal(putData)
	if err != nil {
		fmt.Println("Ошибка сериализации данных:", err)
		return
	}

	time.Sleep(time.Duration(5 * time.Second)) // Эмуляция длительной операции
	// Создание PUT-запроса
	url := "http://127.0.0.1:8000/reserves/update_available/"
	req, err := http.NewRequest("PUT", url, bytes.NewBuffer(jsonData))
	if err != nil {
		fmt.Println("Ошибка создания запроса:", err)
		return
	}

	req.Header.Set("Content-Type", "application/json")

	// Выполнение запроса
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("Ошибка отправки запроса:", err)
		return
	}

	defer resp.Body.Close()

	// Проверка статуса ответа
	if resp.StatusCode == http.StatusOK {
		fmt.Printf("PUT-запрос успешно обработан")
	} else {
		fmt.Println("Не удалось обработать PUT-запрос")
	}
}

func validateKey(key string) bool {
	knownKey := "P-j8TR9-vxbePac3Du1y"
	return key == knownKey
}

func generateRandomBool() bool {
	return rand.Float64() < 0.8
}
