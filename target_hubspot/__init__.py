#!/usr/bin/env python3
import os
import json
import sys
import argparse
import requests
import base64
import pandas as pd
import logging
import backoff

from datetime import datetime, timedelta
from target_hubspot.discover import discover_schemas

from target_hubspot.utils import logger, request, SESSION, request_push


def load_json(path):
    with open(path) as f:
        return json.load(f)


def write_json_file(filename, content):
    with open(filename, 'w') as f:
        json.dump(content, f, indent=4)


def parse_args():
    '''Parse standard command-line args.
    Parses the command-line arguments mentioned in the SPEC and the
    BEST_PRACTICES documents:
    -c,--config     Config file
    Returns the parsed args object from argparse. For each argument that
    point to JSON files (config), we will automatically load and parse 
    the JSON file.
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-c', '--config',
        help='Config file',
        required=True)

    parser.add_argument(
        '-d', '--discover',
        action='store_true',
        help='Do schema discovery')

    args = parser.parse_args()
    if args.config:
        setattr(args, 'config_path', args.config)
        args.config = load_json(args.config)


    return args


def upload_contacts(config, payload):
    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    for p in payload:
        payload_str = json.dumps(dict(properties=p))
        request_push(config, url, payload_str)


def upload_engagements(config, payload):
    url = "https://api.hubapi.com/engagements/v1/engagements"
    for p in payload:
        request_push(config, url, json.dumps(p))


def upload(config, args):
    engagements_file = f"{config['input_path']}/engagements.json"
    if os.path.exists(engagements_file):
        logger.info("Found engagements.json, uploading...")
        with open(engagements_file, "r") as f:
            payload = json.load(f)
        upload_engagements(config, payload)
        logger.info("engagements.json uploaded!")
    
    contacts_file = f"{config['input_path']}/contacts.json"
    if os.path.exists(contacts_file):
        logger.info("Found contacts.json, uploading...")
        with open(contacts_file, "r") as f:
            payload = json.load(f)
        upload_contacts(config, payload)
        logger.info("contacts.json uploaded!")
    
    logger.info("Posting process has completed!")


def do_discover(config):
    logger.info('Loading schemas')
    json.dump(discover_schemas(config), sys.stdout, indent=4)


def main():
    # Parse command line arguments
    args = parse_args()

    if args.discover:
        do_discover(args.config)
    else:
        upload(args.config, args)


if __name__ == "__main__":
    main()
