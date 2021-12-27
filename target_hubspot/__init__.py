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

logger = logging.getLogger("target-hubspot")
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

SESSION = requests.Session()

BASE_URL = "https://api.hubapi.com"

class InvalidAuthException(Exception):
    pass

class SourceUnavailableException(Exception):
    pass


def giveup(exc):
    return exc.response is not None \
        and 400 <= exc.response.status_code < 500 \
        and exc.response.status_code != 429

def on_giveup(details):
    if len(details['args']) == 2:
        url, params = details['args']
    else:
        url = details['args']
        params = {}

    raise Exception("Giving up on request after {} tries with url {} and params {}" \
                    .format(details['tries'], url, params))

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
    -s,--state      State file
    -d,--discover   Run in discover mode
    -p,--properties Properties file: DEPRECATED, please use --catalog instead
    --catalog       Catalog file
    Returns the parsed args object from argparse. For each argument that
    point to JSON files (config, state, properties), we will automatically
    load and parse the JSON file.
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-c', '--config',
        help='Config file',
        required=True)

    args = parser.parse_args()
    if args.config:
        setattr(args, 'config_path', args.config)
        args.config = load_json(args.config)

    return args


def acquire_access_token_from_refresh_token(config):
    payload = {
        "grant_type": "refresh_token",
        "redirect_uri": config['redirect_uri'],
        "refresh_token": config['refresh_token'],
        "client_id": config['client_id'],
        "client_secret": config['client_secret'],
    }

    resp = requests.post(BASE_URL + "/oauth/v1/token", data=payload)
    if resp.status_code == 403:
        raise InvalidAuthException(resp.content)

    resp.raise_for_status()
    auth = resp.json()
    config['access_token'] = auth['access_token']
    config['refresh_token'] = auth['refresh_token']
    config['token_expires'] = (
        datetime.utcnow() + timedelta(seconds=auth['expires_in'] - 600))
    logger.info("Token refreshed. Expires at %s", config['token_expires'])


def get_params_and_headers(config, params):
    """
    This function makes a params object and headers object based on the
    authentication values available. If there is an `hapikey` in the config, we
    need that in `params` and not in the `headers`. Otherwise, we need to get an
    `access_token` to put in the `headers` and not in the `params`
    """
    params = params or {}
    hapikey = config.get('hapikey')
    if hapikey is None:
        if config.get('token_expires') is None or config.get('token_expires') < datetime.utcnow():
            acquire_access_token_from_refresh_token(config)
        headers = {'Authorization': 'Bearer {}'.format(config['access_token'])}
    else:
        params['hapikey'] = hapikey
        headers = {}

    if 'user_agent' in config:
        headers['User-Agent'] = config['user_agent']

    headers["Content-Type"] = "application/json"

    return params, headers


@backoff.on_exception(backoff.constant,
                      (requests.exceptions.RequestException,
                       requests.exceptions.HTTPError),
                      max_tries=5,
                      jitter=None,
                      giveup=giveup,
                      on_giveup=on_giveup,
                      interval=10)
def request(config, url, payload, params=None):

    params, headers = get_params_and_headers(config, params)

    req = requests.Request('POST', url, data=payload, headers=headers, params=params).prepare()
    logger.info("POST %s", req.url)
    resp = SESSION.send(req)
    if resp.status_code == 403:
        raise SourceUnavailableException(resp.content)
    else:
        resp.raise_for_status()
    return resp


def upload_engagements(config, payload):
    url = "https://api.hubapi.com/engagements/v1/engagements"
    for p in payload:
        request(config, url, json.dumps(p))


def upload(config, args):
    engagements_file = f"{config['input_path']}/engagements.json"
    if os.path.exists(engagements_file):
        logger.info("Found engagements.json, uploading...")
        with open(engagements_file, "r") as f:
            payload = json.load(f)
        upload_engagements(config, payload)
        logger.info("engagements.json uploaded!")
    
    logger.info("Posting process has completed!")


def main():
    # Parse command line arguments
    args = parse_args()

    # Upload the new QBO data
    upload(args.config, args)


if __name__ == "__main__":
    main()
