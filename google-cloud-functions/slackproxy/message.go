package function

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"cloud.google.com/go/pubsub"
	"github.com/multiplay/go-slack/chat"
)

// publishMessage message and returns message ID
func publishMessage(ctx context.Context, projectID, topicID string, msg chat.Message) (string, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	b, err := json.Marshal(msg)
	if err != nil {
		return "", err
	}

	t := pubsubClient.Topic(topicID)
	result := t.Publish(ctx, &pubsub.Message{
		Data: b,
	})

	// Block until the result is returned and a server-generated
	// ID is returned for the published message.
	id, err := result.Get(ctx)
	if err != nil {
		return "", fmt.Errorf("publish result.Get: %v", err)
	}

	return id, nil
}

func readMessage(b []byte) (chat.Message, error) {
	msg := chat.Message{}
	err := json.Unmarshal(b, &msg)
	if err != nil {
		return chat.Message{}, err
	}

	return msg, nil
}

func validateMessage(m chat.Message) error {
	if m.Username == "" {
		return fmt.Errorf("Username is empty")
	}
	return nil
}
