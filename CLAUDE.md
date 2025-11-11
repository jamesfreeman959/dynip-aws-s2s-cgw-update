# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python application that automatically updates AWS Customer Gateway (CGW) IP addresses when the local public IP changes. It's designed to maintain AWS Site-to-Site VPN connections when using a dynamic IP address on the customer side.

The application:
1. Periodically checks the current public IP (via ipify.org)
2. Compares it with the IP configured in the AWS Customer Gateway
3. If different, creates a new Customer Gateway with the updated IP
4. Modifies the VPN connection to use the new Customer Gateway
5. Deletes the old Customer Gateway

## Architecture

**Single-file application**: All logic is in `main.py` with no separate modules or classes.

**Execution model**: The app runs as a long-lived process using Python's `schedule` library to check every 5 minutes (configured at main.py:79). This replaces an earlier crontab-based approach.

**AWS interaction flow**:
1. Query VPN connections to get the Customer Gateway ID
2. Query Customer Gateway details to get the current configured IP
3. Compare with actual public IP from ipify.org
4. If mismatch: create new CGW → modify VPN connection → delete old CGW

**Configuration**: The application expects the `CGW_NAME` environment variable for tagging new Customer Gateways. It will run without it but won't apply tags.

## Docker Container

The application is containerized and designed to run continuously in Docker.

**Deployment Options**:
- **Docker Compose**: See `docker-compose.yml` and `QUICKSTART.md` (recommended for most users)
- **Docker Swarm**: See `docker-stack.yml` and `DOCKER_SWARM_DEPLOYMENT.md` (for legacy Swarm clusters)
- **Docker CLI**: Manual `docker run` commands (see `QUICKSTART.md`)

**Build the container**:
```bash
docker build -t dynip-aws-s2s-cgw-update .
```

Note: The container uses Python 3.11 and includes the AWS Signing Helper for IAM Roles Anywhere support.

## AWS Permissions and Authentication

The application requires specific EC2 permissions (see `iam-policy.json`):
- `ec2:DescribeVpnConnections`
- `ec2:DescribeCustomerGateways`
- `ec2:CreateCustomerGateway`
- `ec2:ModifyVpnConnection`
- `ec2:DeleteCustomerGateway`
- `ec2:CreateTags`

**Authentication Methods** (in order of preference):

1. **IAM Roles Anywhere** (Recommended for on-premises/non-AWS environments)
   - Uses X.509 certificates for authentication
   - Credentials auto-refresh every hour
   - No static credentials needed
   - See `IAM_ROLES_ANYWHERE_SETUP.md` for complete setup instructions
   - Requires environment variables: `ROLESANYWHERE_CERTIFICATE_PATH`, `ROLESANYWHERE_PRIVATE_KEY_PATH`, `ROLESANYWHERE_TRUST_ANCHOR_ARN`, `ROLESANYWHERE_PROFILE_ARN`, `ROLESANYWHERE_ROLE_ARN`, `AWS_REGION`

2. **Default Credential Chain** (Fallback)
   - If IAM Roles Anywhere variables are not set, falls back to standard boto3 credential chain
   - Can use EC2 instance profiles, ECS task roles, or environment variables
   - For static credentials (not recommended): `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`

## Development

**Install dependencies**:
```bash
pip3 install -r requirements.txt
```

**Run locally**:
```bash
python3 main.py
```

**Test AWS connectivity**:
```bash
aws ec2 describe-vpn-connections
```

## Key Assumptions and Limitations

- The code assumes there is exactly one VPN connection and retrieves index [0]
- No error handling for network failures when checking public IP
- No graceful shutdown handling for the infinite loop
- No logging beyond print statements
- Customer Gateway deletion happens immediately after VPN connection modification (no verification that modification succeeded)
