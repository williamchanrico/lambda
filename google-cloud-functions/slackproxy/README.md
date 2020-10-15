## Slack Proxy

> A simple HTTP and Background function to receive/send Slack Webhook notification.

No more leaks on these `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`

<center><img src="./slackproxy.png" width="500" /></center>

1. Avoids injecting Slack Webhook Token in simple scripts all over the place
2. Provides a place to aggregate and work on Slack notification traffic
3. Acts as optional middleware in-case we want to expand the dumb proxy into a more generic alerting proxy/platform
