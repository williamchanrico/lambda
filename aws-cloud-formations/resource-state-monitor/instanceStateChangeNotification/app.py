#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to report manual instance creation events to Slack.
This script will listen for CloudWatch Event Rule instance_state_change events
and will query CloudTrail & EC2 for any manual instance creation events.
It will report details of that event via Slack webhook.
"""

# Title: instanceStateChangeNotification
# Description: Report any manual instance creation events on AWS
# Author: William Chanrico
# Date: 18-May-2020

import os
import json
import logging
import requests
from dateutil import parser
from datetime import timedelta

import boto3

EC2_CLIENT = None
CLOUD_TRAIL_CLIENT = None


def describe_instance(instance_id):
    global EC2_CLIENT

    response = EC2_CLIENT.describe_instances(InstanceIds=[instance_id])
    if len(response["Reservations"]) <= 0:
        return []
    return response["Reservations"][0]["Instances"]


def lookup_events(event_name, resource_name):
    global CLOUD_TRAIL_CLIENT

    response = CLOUD_TRAIL_CLIENT.lookup_events(
        LookupAttributes=[{
            'AttributeKey': 'ResourceName',
            'AttributeValue': resource_name
        }, {
            'AttributeKey': 'EventName',
            'AttributeValue': event_name
        }])
    if len(response["Events"]) <= 0:
        return []
    return response["Events"]


def init(event, context):
    global EC2_CLIENT, CLOUD_TRAIL_CLIENT
    EC2_CLIENT = boto3.client('ec2')
    CLOUD_TRAIL_CLIENT = boto3.client('cloudtrail')


def lambda_handler(event, context):
    init(event, context)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    slack_channel = os.getenv("SLACK_CHANNEL")
    if not slack_webhook_url:
        raise Exception('SLACK_WEBHOOK_URL is not set')

    event_instance_id = event.get("detail")["instance-id"]
    event_region_id = event.get("region")
    event_instance_state = event.get("detail")["state"]
    if event_instance_state.lower() != "running":
        return "Ignoring non-Running instance"

    # Before triggering this, we should wait for AWS's Backend to propagate
    # the instance creation event.
    # This prevents No Resource Found error
    #
    # https://forums.aws.amazon.com/thread.jspa?threadID=171777

    instances = describe_instance(event_instance_id)
    if len(instances) <= 0:
        return "Instance not found"
    logger.info("Instance: {}".format(str(instances)))
    instance = instances[0]

    trail_events = lookup_events("RunInstances", event_instance_id)
    if len(trail_events) <= 0:
        return "Trail Events not found"
    logger.info("TrailEvents: {}".format(str(trail_events)))

    trail_events = [
        x for x in trail_events if x["EventName"] == "RunInstances"
    ]
    trail_event = json.loads(trail_events[0]["CloudTrailEvent"])
    logger.info("New instance creation event: {}".format(
        str(json.dumps(trail_event, indent=4))))

    # Default is UTC tz, we want user-friendly GMT+7 formatted time
    trail_event_event_time_obj = parser.parse(
        trail_event["eventTime"]) + timedelta(hours=7)
    trail_event_event_time = trail_event_event_time_obj.strftime(
        "%b %d %Y %H:%M:%S") + " WIB"

    if "userAgent" not in trail_event:
        trail_event["userAgent"] = "Empty UserAgent"

    slack_message = '_{}_ has created an instance: *{}* ({})\n> _{}_'.format(
        trail_event["userIdentity"]["userName"], event_instance_id,
        instance["PrivateIpAddress"], trail_event["userAgent"])

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
                '*Instance Type:*\n{} ({} vCPU)'.format(
                    instance["InstanceType"],
                    instance["CpuOptions"]["CoreCount"])
            }, {
                'type': 'mrkdwn',
                'text': '*When:*\n{}'.format(trail_event_event_time)
            }, {
                'type':
                'mrkdwn',
                'text':
                '*Key Pair:*\n{}'.format(
                    trail_event["requestParameters"]["instancesSet"]["items"]
                    [0]["keyName"])
            }, {
                'type':
                'mrkdwn',
                'text':
                '*Source IP:*\n{}'.format(trail_event["sourceIPAddress"])
            }, {
                'type':
                'mrkdwn',
                'text':
                '*Security Group:*\n{}'.format(
                    instance["SecurityGroups"][0]["GroupName"])
            }, {
                'type':
                'mrkdwn',
                'text':
                '*Region ID:*\n{}'.format(trail_event["awsRegion"])
            }]
        }, {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': 'CC: <!subteam^XYZ>'
            },
            'accessory': {
                'type':
                'button',
                'text': {
                    'type': 'plain_text',
                    'text': 'Go to Console'
                },
                'url':
                'https://ap-southeast-1.console.aws.amazon.com/ec2/v2/home?region={}#Instances:search={};sort=desc:launchTime'
                .format(event_region_id, event_instance_id)
            }
        }],
        'icon_emoji':
        ':pepecop:',
        'username':
        'Bang AWS',
        'channel':
        slack_channel
    }
    headers = {'Content-type': 'application/json'}
    logger.info("slack_message: {}".format(str(slack_payload)))
    slack_response = requests.post(slack_webhook_url,
                                   headers=headers,
                                   data=json.dumps(slack_payload))
    logger.info("slack_response: " + str(slack_response))
    return {'statusCode': 200, 'body': str(slack_response)}
