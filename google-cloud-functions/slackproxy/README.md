## Slack Proxy

> A simple HTTP and Background function to receive/send Slack Webhook notification (instead of hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX)

```
client --> slack-proxy/PublishMessage --> pub/sub <-- slack-proxy/ConsumeMessage --> https://hooks.slack.com/services/XXX
```

1. Avoid the needs for simple internal scripts holding Slack Webhook URL token
2. Provides a place to aggeragte and work with Slack notification traffic
3. Acting as optional middleware in-case we want to expand the dumb proxy into a more generic alerting proxy/platform
