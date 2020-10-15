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

func helpMessage() string {
	return `
// Message represents slack chat message.
type Message struct {
	// Token is the Authentication token (Requires scope: chat:write:bot or chat:write:user).
	Token string 'json:"token,omitempty"'

	// Channel is the channel, private group, or IM channel to send message to.
	Channel string 'json:"channel,omitempty"'

	// Text of the message to send.
	Text string 'json:"text,omitempty"'

	// Markdown enables Markdown support.
	Markdown bool 'json:"mrkdwn,omitempty"'

	// Parse changes how messages are treated.
	Parse string 'json:"parse,omitempty"'

	// LinkNames causes link channel names and usernames to be found and linked.
	LinkNames int 'json:"link_name,omitempty"'

	// Attachments is structured message attachments
	Attachments []*Attachment 'json:"attachments,omitempty"'

	// UnfurLinks enables unfurling of primarily text-based content.
	UnfurlLinks bool 'json:"unfurl_links,omitempty"'

	// UnfurlMedia if set to false disables unfurling of media content.
	UnfurlMedia bool 'json:"unfurl_media,omitempty"'

	// Username set your bot's user name.
	// Must be used in conjunction with AsUser set to false, otherwise ignored.
	Username string 'json:"username,omitempty"'

	// AsUser pass true to post the message as the authed user, instead of as a bot.
	AsUser bool 'json:"as_user"'

	// IconURL is the URL to an image to use as the icon for this message.
	// Must be used in conjunction with AsUser set to false, otherwise ignored.
	IconURL string 'json:"icon_url,omitempty"'

	// IconEmoji is the emoji to use as the icon for this message.
	// Overrides IconURL.
	// Must be used in conjunction with AsUser set to false, otherwise ignored.
	IconEmoji string 'json:"icon_emoji,omitempty"'

	// ThreadTS is the timestamp (ts) of the parent message to reply to a thread.
	ThreadTS string 'json:"thread_ts,omitempty"'

	// ReplyBroadcast used in conjunction with thread_ts and indicates whether reply
	// should be made visible to everyone in the channel or conversation.
	ReplyBroadcast bool 'json:"reply_broadcast,omitempty"'
}
`
}
