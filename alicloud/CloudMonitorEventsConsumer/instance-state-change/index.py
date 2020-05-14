#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test of Lambda equivalent on Alicloud called Function Compute.
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
import requests
from dateutil import parser
from datetime import timedelta

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkecs.request.v20140526 import DescribeInstancesRequest
from aliyunsdkactiontrail.request.v20171204 import LookupEventsRequest

ACS_CLIENT = None


def describe_instance(instance_id):
    global ACS_CLIENT

    request = DescribeInstancesRequest.DescribeInstancesRequest()
    request.add_query_param("SecurityToken", os.getenv("securityToken"))
    request.set_PageSize(10)
    request.set_InstanceIds([instance_id])

    response = ACS_CLIENT.do_action_with_exception(request)
    return json.loads(response)


def lookup_events(event_name, resource_name):
    global ACS_CLIENT

    request = LookupEventsRequest.LookupEventsRequest()
    request.add_query_param("SecurityToken", os.getenv("securityToken"))
    request.set_EventName(event_name)
    request.set_ResourceName(resource_name)

    response = ACS_CLIENT.do_action_with_exception(request)
    return json.loads(response)


def init(event, context):
    evt = json.loads(event)
    region_id = evt.get("regionId")

    global ACS_CLIENT
    ACS_CLIENT = AcsClient(os.getenv("accessKeyID"),
                           os.getenv("accessKeySecret"), region_id)


def handler(event, context):
    init(event, context)
    logger = logging.getLogger()
    logger.info("New instance has been detected!")

    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    slack_channel = os.getenv("SLACK_CHANNEL")
    if not slack_webhook_url:
        raise Exception('SLACK_WEBHOOK_URL is not set')

    evt = json.loads(event)
    instance_id = evt.get("content")["resourceId"]
    region_id = evt.get("regionId")
    event_instance_state = evt.get("content")["state"]
    if event_instance_state != "Running":
        return "Ignoring non-Running instance"

    # Wait for Alicloud's Backend to propagate the instance creation event
    # This prevents No Resource Found error
    time.sleep(15)

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
    trail_event_key_pair_name = trail_event["requestParameters"]["KeyPairName"]
    trail_event_instance_name = trail_event["requestParameters"][
        "InstanceName"]
    trail_event_instance_type = trail_event["requestParameters"][
        "InstanceType"]
    trail_event_source_ip_address = trail_event["sourceIpAddress"]

    trail_event_user_agent = ""
    try:
        trail_event_user_agent = trail_event["userAgent"]
    except KeyError:
        pass

    trail_event_user_name = trail_event["userIdentity"]["userName"]
    trail_event_event_time_obj = parser.parse(
        trail_event["eventTime"]) + timedelta(hours=7)
    trail_event_event_time = trail_event_event_time_obj.strftime(
        "%b %d %Y %H:%M:%S") + " WIB"

    if trail_event_user_agent != "":
        slack_message = '*{}* has created an instance: _{}_\n> _{}_'.format(
            trail_event_user_name, trail_event_instance_name,
            trail_event_user_agent)
    else:
        slack_message = '*{}* has created an instance: _{}_\n'.format(
            trail_event_user_name, trail_event_instance_name)

    slack_payload = {
        'blocks': [{
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': slack_message
            }
        }, {
            'type':
            'section',
            'fields': [{
                'type':
                'mrkdwn',
                'text':
                '*Instance Type:*\n{}'.format(trail_event_instance_type)
            }, {
                'type': 'mrkdwn',
                'text': '*When:*\n{}'.format(trail_event_event_time)
            }, {
                'type':
                'mrkdwn',
                'text':
                '*Key Pair:*\n{}'.format(trail_event_key_pair_name)
            }, {
                'type':
                'mrkdwn',
                'text':
                '*Source IP:*\n{}'.format(trail_event_source_ip_address)
            }]
        }, {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': '.'
            },
            'accessory': {
                'type':
                'button',
                'text': {
                    'type': 'plain_text',
                    'text': 'Go to Console'
                },
                'url':
                'https://ecs.console.aliyun.com/#/server/{}/detail?regionId={}'
                .format(instance_id, region_id)
            }
        }],
        'icon_emoji':
        ':topedbersih:',
        'username':
        'Bang Ali',
        'channel':
        slack_channel
    }
    headers = {'Content-type': 'application/json'}
    slack_response = requests.post(slack_webhook_url,
                                   headers=headers,
                                   data=json.dumps(slack_payload))
    logger.info('slack_response:', slack_response)
    return 'OK'
