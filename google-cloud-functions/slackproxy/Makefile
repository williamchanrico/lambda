.PHONY: test clean all

PROJECT_ID      := "project-id"
TOPIC_ID        := "slack-proxy"
SERVICE_ACCOUNT := "slack-proxy@$(PROJECT_ID).iam.gserviceaccount.com"

.PHONY: dev
dev:
	PROJECT_ID=temp-project \
		TOPIC_ID=temp-topic \
		LOG_LEVEL=debug \
		SLACK_CHANNEL="#temp-channel" \
		SLACK_WEBHOOK_URL="https://hooks.slack.com/services/TTT/YYY/XXX" \
		go run cmd/main.go

.PHONY: publisher
publisher:
	gcloud --project=$(PROJECT_ID) functions deploy publish-slack-message \
		--allow-unauthenticated \
		--entry-point=PublishMessage \
		--runtime=go113 \
		--service-account=$(SERVICE_ACCOUNT) \
		--timeout=15 \
		--trigger-http \
		--region=asia-southeast2 \
		--env-vars-file=./.env.yaml \
		--ingress-settings=internal-only

.PHONY: consumer
consumer:
	gcloud --project=$(PROJECT_ID) functions deploy consume-slack-message \
		--allow-unauthenticated \
		--entry-point=ConsumeMessage \
		--runtime=go113 \
		--service-account=$(SERVICE_ACCOUNT) \
		--timeout=15 \
		--trigger-topic=$(TOPIC_ID) \
		--region=asia-southeast2 \
		--env-vars-file=./.env.yaml \
		--ingress-settings=internal-only
