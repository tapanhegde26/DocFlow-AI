import boto3
import json
import os
from common.services.logger import log_to_cloudwatch

# Environment configuration
region = os.environ.get("AWS_REGION", "ca-central-1")

ssm = boto3.client("ssm", region_name=region)
secretsmanager = boto3.client("secretsmanager", region_name=region)

_cached_config = {}
_cached_secret = {}

def get_parameter(name, with_decryption=True):
    if name in _cached_config:
        return _cached_config[name]
    response = ssm.get_parameter(Name=name, WithDecryption=with_decryption)
    value = response['Parameter']['Value']
    _cached_config[name] = value
    return value

def get_secret(secret_name):
    if secret_name in _cached_secret:
        return _cached_secret[secret_name]
    response = secretsmanager.get_secret_value(SecretId=secret_name)
    secret = response['SecretString']
    _cached_secret[secret_name] = json.loads(secret)
    return _cached_secret[secret_name]