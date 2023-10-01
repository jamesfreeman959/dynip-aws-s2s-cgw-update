#!/usr/bin/env python3
import boto3
from botocore.exceptions import ClientError
from requests import get
import os
import schedule
import time

try:
    cgwName = os.environ['CGW_NAME']
except:
    cgwName = ''

print("App started... CGW Name is: " + cgwName)

def cgwUpdate():

    client = boto3.client('ec2')


    try:
        vpns = client.describe_vpn_connections()
        cgwId=vpns["VpnConnections"][0]["CustomerGatewayId"]
    except ClientError as e:
        print('Error', e)

    try:
        cgw = client.describe_customer_gateways(
            CustomerGatewayIds=[
            cgwId,
        ],
    )
        cgwIp = cgw["CustomerGateways"][0]["IpAddress"]
    except ClientError as e:
        print('Error', e)

    ip = get('https://api.ipify.org').content.decode('utf8')
    print('My public IP address is: {}'.format(ip))

    if cgwIp == ip:
        print("Matches")
    else:
        print("Differs")
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
        except ClientError as e:
            print('Error', e)

        try:
            update = client.modify_vpn_connection(
                    VpnConnectionId=vpns["VpnConnections"][0]["VpnConnectionId"],
                    CustomerGatewayId=newcgw["CustomerGateway"]["CustomerGatewayId"],
                )
        except ClientError as e:
            print('Error', e)

        try:
            delete = client.delete_customer_gateway(
                CustomerGatewayId=cgw["CustomerGateways"][0]["CustomerGatewayId"]
                )
        except ClientError as e:
            print('Error', e)

schedule.every(5).minutes.do(cgwUpdate)

while True:
    schedule.run_pending()
    time.sleep(1)

