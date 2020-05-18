# Function Compute

> Alibaba Cloud Function Compute is an event-driven and fully-managed compute service. With Function Compute, you can quickly build any type of applications or services without considering management or O&M. You can complete a set of backend services for processing multimedia data even in several days.

![fc](http://docs-aliyun.cn-hangzhou.oss.aliyun-inc.com/assets/pic/52895/intl_en/1524015384520/TheProcedure...png)

## CloudMonitorEventsConsumer

Service containing functions that will process Alicloud Cloud Monitor events

### instance-state-change

Function that will send alerts to slack whenever there's a manually created instance.

Will send details of the action. E.g. username, sourceIP, instanceType, userAgent, etc.

Does not include instance spawned by ESS autoscaling groups.

```
Alicloud CMS -> Function Compute -> Slack
```
