package function

import (
	"context"
	"fmt"
	"io/ioutil"
	"net/http"

	"cloud.google.com/go/pubsub"

	log "github.com/sirupsen/logrus"
)

// PublishMessage validate and write Slack webhook request to pubsub
func PublishMessage(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	resp := ""

	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		resp = fmt.Sprintf("Failed to read request body: %v", err)
		log.Error(resp)
		http.Error(w, resp, http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	msg, err := readMessage(body)
	if err != nil {
		resp = fmt.Sprintf("Failed to read message from body: %v", err)
		log.Error(resp)
		http.Error(w, resp, http.StatusBadRequest)
		return
	}

	err = validateMessage(msg)
	if err != nil {
		resp = fmt.Sprintf("Invalid message: %v", err)
		log.Error(resp)
		http.Error(w, resp, http.StatusBadRequest)
		return
	}

	log.Debugf("Publishing to projectID=%v topicID=%v: %#v", projectID, topicID, string(body))
	msgID, err := publishMessage(ctx, projectID, topicID, msg)
	if err != nil {
		resp = fmt.Sprintf("Failed to publish: %v", err)
		log.Errorf(resp)
		http.Error(w, resp, http.StatusInternalServerError)
		return
	}

	resp = fmt.Sprintf("Successfully published message with ID: %v\n", msgID)
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(resp))

	return
}

// ConsumeMessage consume and validate Slack webhook payload from pubsub, then submit to Slack API
func ConsumeMessage(ctx context.Context, m pubsub.Message) error {
	msg, err := readMessage(m.Data)
	if err != nil {
		return err
	}

	err = validateMessage(msg)
	if err != nil {
		return err
	}

	_, err = msg.Send(slackClient)
	if err != nil {
		return err
	}

	return nil
}
