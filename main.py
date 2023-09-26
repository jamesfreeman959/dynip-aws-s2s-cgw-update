#!env python3
import boto3
from botocore.exceptions import ClientError


ec2 = boto3.client('ec2',
               aws_access_key_id='',
               aws_secret_access_key='',
               region_name=''
               )

try:
    result = ec2.describe_vpn_connections()
    print(result)
except ClientError as e:
    print('Error', e)

try:
    result = ec2.describe_customer_gateways()
    print(result)
except ClientError as e:
    if 'DryRunOperation' not in str(e):
        print("You don't have permission to reboot instances.")
        raise

try:
    response = ec2.reboot_instances(InstanceIds=['INSTANCE_ID'], DryRun=False)
    print('Success', response)
except ClientError as e:
    print('Error', e)
