#!/usr/bin/env python3
import boto3
from botocore.exceptions import ClientError
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session
from requests import get
import os
import schedule
import time
import subprocess
import json
from datetime import datetime, timezone

try:
    cgwName = os.environ['CGW_NAME']
except:
    cgwName = ''

# IAM Roles Anywhere configuration
CERTIFICATE_PATH = os.environ.get('ROLESANYWHERE_CERTIFICATE_PATH')
PRIVATE_KEY_PATH = os.environ.get('ROLESANYWHERE_PRIVATE_KEY_PATH')
TRUST_ANCHOR_ARN = os.environ.get('ROLESANYWHERE_TRUST_ANCHOR_ARN')
PROFILE_ARN = os.environ.get('ROLESANYWHERE_PROFILE_ARN')
ROLE_ARN = os.environ.get('ROLESANYWHERE_ROLE_ARN')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

print("App started... CGW Name is: " + cgwName)

def get_roles_anywhere_credentials():
    """
    Fetch temporary credentials using IAM Roles Anywhere.
    This function is called automatically by boto3 when credentials need refresh.
    """
    if not all([CERTIFICATE_PATH, PRIVATE_KEY_PATH, TRUST_ANCHOR_ARN, PROFILE_ARN, ROLE_ARN]):
        print("IAM Roles Anywhere not configured, falling back to default credential chain")
        return None

    try:
        cmd = [
            'aws_signing_helper', 'credential-process',
            '--certificate', CERTIFICATE_PATH,
            '--private-key', PRIVATE_KEY_PATH,
            '--trust-anchor-arn', TRUST_ANCHOR_ARN,
            '--profile-arn', PROFILE_ARN,
            '--role-arn', ROLE_ARN,
            '--region', AWS_REGION
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        creds = json.loads(result.stdout)

        return {
            'access_key': creds['AccessKeyId'],
            'secret_key': creds['SecretAccessKey'],
            'token': creds['SessionToken'],
            'expiry_time': creds['Expiration']
        }
    except subprocess.CalledProcessError as e:
        print(f"Error obtaining credentials from IAM Roles Anywhere: {e.stderr}")
        raise
    except Exception as e:
        print(f"Error parsing credentials: {e}")
        raise

def get_boto3_session():
    """
    Create a boto3 session with auto-refreshing IAM Roles Anywhere credentials.
    """
    if not all([CERTIFICATE_PATH, PRIVATE_KEY_PATH, TRUST_ANCHOR_ARN, PROFILE_ARN, ROLE_ARN]):
        # Fall back to default credential chain (env vars, instance profile, etc.)
        print("Using default AWS credential chain")
        return boto3.Session(region_name=AWS_REGION)

    print("Using IAM Roles Anywhere for credentials")

    session = get_session()

    def refresh():
        """Refresh credentials - called automatically before expiration"""
        creds = get_roles_anywhere_credentials()
        return {
            'access_key': creds['access_key'],
            'secret_key': creds['secret_key'],
            'token': creds['token'],
            'expiry_time': creds['expiry_time']
        }

    # Initial credential fetch
    initial_creds = get_roles_anywhere_credentials()

    # Create refreshable credentials
    refreshable_credentials = RefreshableCredentials.create_from_metadata(
        metadata=initial_creds,
        refresh_using=refresh,
        method='custom-roles-anywhere'
    )

    # Attach to session
    session._credentials = refreshable_credentials
    session.set_config_variable('region', AWS_REGION)

    return boto3.Session(botocore_session=session)

# Create session once at module level (credentials will auto-refresh)
boto3_session = get_boto3_session()

def cgwUpdate():
    from datetime import datetime

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting IP check...")

    client = boto3_session.client('ec2')

    try:
        vpns = client.describe_vpn_connections()
        cgwId=vpns["VpnConnections"][0]["CustomerGatewayId"]
        print(f"  Found VPN connection with Customer Gateway ID: {cgwId}")
    except ClientError as e:
        print(f'  Error fetching VPN connections: {e}')
        return

    try:
        cgw = client.describe_customer_gateways(
            CustomerGatewayIds=[
            cgwId,
        ],
    )
        cgwIp = cgw["CustomerGateways"][0]["IpAddress"]
        print(f"  Current CGW IP in AWS: {cgwIp}")
    except ClientError as e:
        print(f'  Error fetching Customer Gateway: {e}')
        return

    try:
        ip = get('https://api.ipify.org').content.decode('utf8')
        print(f'  My public IP address: {ip}')
    except Exception as e:
        print(f'  Error fetching public IP: {e}')
        return

    if cgwIp == ip:
        print("  ✓ IPs match - no update needed")
    else:
        print(f"  ✗ IPs differ - updating Customer Gateway...")
        try:
            newcgw = client.create_customer_gateway(
                BgpAsn=int(cgw["CustomerGateways"][0]["BgpAsn"]),
                PublicIp=ip,
                Type=cgw["CustomerGateways"][0]["Type"],
                TagSpecifications=[
                    {
                        'ResourceType': 'customer-gateway',
                        'Tags': [
                            {
                                'Key': 'Name',
                                'Value': cgwName
                            },
                        ]
                    },
                ],
            )
            new_cgw_id = newcgw["CustomerGateway"]["CustomerGatewayId"]
            print(f"    Created new Customer Gateway: {new_cgw_id}")
        except ClientError as e:
            print(f'    Error creating Customer Gateway: {e}')
            return

        try:
            update = client.modify_vpn_connection(
                    VpnConnectionId=vpns["VpnConnections"][0]["VpnConnectionId"],
                    CustomerGatewayId=new_cgw_id,
                )
            print(f"    Updated VPN connection to use new Customer Gateway")
        except ClientError as e:
            print(f'    Error updating VPN connection: {e}')
            return

        try:
            old_cgw_id = cgw["CustomerGateways"][0]["CustomerGatewayId"]
            delete = client.delete_customer_gateway(
                CustomerGatewayId=old_cgw_id
                )
            print(f"    Deleted old Customer Gateway: {old_cgw_id}")
            print(f"  ✓ Update complete!")
        except ClientError as e:
            print(f'    Error deleting old Customer Gateway: {e}')

# Run immediately on startup
print("Running initial check...")
cgwUpdate()

# Then schedule to run every 5 minutes
schedule.every(5).minutes.do(cgwUpdate)

print("Scheduled to check every 5 minutes. Running...")
while True:
    schedule.run_pending()
    time.sleep(1)

