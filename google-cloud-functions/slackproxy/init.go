package function

import (
	"context"
	"os"

	"cloud.google.com/go/pubsub"
	"github.com/multiplay/go-slack/webhook"
	log "github.com/sirupsen/logrus"
)

var (
	projectID       string
	topicID         string
	slackWebhookURL string
)

var pubsubClient *pubsub.Client
var slackClient *webhook.Client

// init cold start
func init() {
	var err error

	// Logging
	logLevelString := os.Getenv("LOG_LEVEL")
	if logLevelString == "" {
		logLevelString = "info"
	}
	logLevel, err := log.ParseLevel(logLevelString)
	if err != nil {
		log.Fatal(err)
	}
	log.SetLevel(logLevel)

	// Env
	projectID = mustGetenv("PROJECT_ID")
	topicID = mustGetenv("TOPIC_ID")
	slackWebhookURL = mustGetenv("SLACK_WEBHOOK_URL")

	// Pubsub Client
	pubsubClient, err = pubsub.NewClient(context.Background(), projectID)
	if err != nil {
		log.Fatalf("pubsub.NewClient: %v", err)
	}

	// Slack Client
	slackClient = webhook.New(slackWebhookURL)
}

// mustGetenv returns env value or panic if unspecified
func mustGetenv(key string) string {
	value := os.Getenv(key)
	if value == "" {
		log.Fatalf("%v is empty", key)
	}

	log.Debugf("Env %v: %v", key, value)

	return value
}
