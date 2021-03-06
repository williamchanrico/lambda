#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trying Lambda equivalent on Alicloud called Function Compute.
This script will listen for CloudMonitorService webhook instance:state_change,
and will then query ActionTrails for any manual instance creation events.
It will report details of that event via Slack webhook.
"""

# Title: instance-state-change
# Description: Report any manual instance creation events on Alicloud
# Author: William Chanrico
# Date: 13-May-2020

import os
import json
import time
import logging
from datetime import timedelta
from dateutil import parser
import requests

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkecs.request.v20140526 import DescribeInstancesRequest
from aliyunsdkactiontrail.request.v20171204 import LookupEventsRequest

ACS_CLIENT = None


def describe_instance(instance_id):
    """ Describe an ECS instance """
    global ACS_CLIENT

    request = DescribeInstancesRequest.DescribeInstancesRequest()
    request.add_query_param("SecurityToken", os.getenv("securityToken"))
    request.set_PageSize(10)
    request.set_InstanceIds([instance_id])

    response = ACS_CLIENT.do_action_with_exception(request)
    return json.loads(response)


def lookup_events(event_name, resource_name):
    """ Lookup ActionTrails event """
    global ACS_CLIENT

    request = LookupEventsRequest.LookupEventsRequest()
    request.add_query_param("SecurityToken", os.getenv("securityToken"))
    request.set_EventName(event_name)
    request.set_ResourceName(resource_name)

    response = ACS_CLIENT.do_action_with_exception(request)
    return json.loads(response)


def init(event, context):
    """ Initialize global components """
    evt = json.loads(event)
    region_id = evt.get("regionId")

    global ACS_CLIENT
    ACS_CLIENT = AcsClient(os.getenv("accessKeyID"), os.getenv("accessKeySecret"), region_id)


def handler(event, context):
    """ Main entrypoint """
    init(event, context)
    logger = logging.getLogger()

    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    slack_channel = os.getenv("SLACK_CHANNEL")
    if not slack_webhook_url:
        raise Exception("SLACK_WEBHOOK_URL is not set")

    evt = json.loads(event)
    instance_id = evt.get("content")["resourceId"]
    region_id = evt.get("regionId")
    event_instance_state = evt.get("content")["state"]
    if event_instance_state != "Running":
        return "Ignoring non-Running instance"

    # Wait for Alicloud's Backend to propagate the instance creation event
    # This prevents No Resource Found error
    time.sleep(7)

    instances = describe_instance(instance_id)
    if instances["TotalCount"] <= 0:
        return "Instance not found"
    instance = instances["Instances"]["Instance"][0]
    if instance["Description"] == "ESS":
        return "Instance is spawned via ESS Autoscale"

    trail_events = lookup_events("RunInstance", instance_id)
    if len(trail_events) <= 0:
        return "Trail Events not found"

    trail_event = trail_events["Events"][0]
    logger.info("New instance creation event: %s", str(json.dumps(trail_event, indent=4)))

    # Default is UTC tz, we want user-friendly GMT+7 formatted time
    trail_event_event_time_obj = parser.parse(trail_event["eventTime"]) + timedelta(hours=7)
    trail_event_event_time = trail_event_event_time_obj.strftime("%b %d %Y %H:%M:%S") + " WIB"

    if "userAgent" not in trail_event:
        trail_event["userAgent"] = "Empty UA (Web Console activities show no UA in the background API calls)"

    slack_message = "_{}_ has created an instance: *{}*\n> _{}_".format(
        trail_event["userIdentity"]["userName"],
        trail_event["requestParameters"]["InstanceName"],
        trail_event["userAgent"],
    )

    slack_payload = {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": slack_message}},
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Instance Type:*\n{}".format(trail_event["requestParameters"]["InstanceType"]),
                    },
                    {"type": "mrkdwn", "text": "*When:*\n{}".format(trail_event_event_time)},
                    {
                        "type": "mrkdwn",
                        "text": "*Key Pair:*\n{}".format(trail_event["requestParameters"]["KeyPairName"]),
                    },
                    {"type": "mrkdwn", "text": "*Source IP:*\n{}".format(trail_event["sourceIpAddress"])},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "☕"},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Go to Console"},
                    "url": "https://ecs.console.aliyun.com/#/server/{}/detail?regionId={}".format(
                        instance_id, region_id
                    ),
                },
            },
        ],
        "icon_emoji": ":topedbersih:",
        "username": "Bang Ali",
        "channel": slack_channel,
    }
    headers = {"Content-type": "application/json"}
    slack_response = requests.post(slack_webhook_url, headers=headers, data=json.dumps(slack_payload))
    return "OK"
