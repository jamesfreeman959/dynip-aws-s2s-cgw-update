# AWS Site-to-Site VPN Dynamic IP Updater

Automatically updates AWS Customer Gateway IP addresses when your public IP changes, maintaining Site-to-Site VPN connections with dynamic IP addresses.

## Overview

This application monitors your public IP address and automatically updates your AWS Customer Gateway configuration when it changes. Perfect for maintaining AWS Site-to-Site VPN connections from locations with dynamic IP addresses (home networks, small offices, etc.).

**Key Features:**
- 🔄 Automatic IP monitoring every 5 minutes
- 🔐 Secure authentication using IAM Roles Anywhere (no static credentials)
- 🐳 Containerized for easy deployment
- 🔁 Auto-refreshing AWS credentials (runs indefinitely)
- 📝 Detailed logging for monitoring and troubleshooting

## How It Works

1. Checks your current public IP address via ipify.org
2. Compares with the IP configured in your AWS Customer Gateway
3. If different:
   - Creates a new Customer Gateway with the updated IP
   - Modifies the VPN connection to use the new gateway
   - Deletes the old Customer Gateway
4. Repeats every 5 minutes

## Prerequisites

- Python 3.11+ or Docker
- AWS account with appropriate permissions
- IAM Roles Anywhere configured (see setup guide)
- An existing AWS Site-to-Site VPN connection

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd dynip-aws-s2s-cgw-update

# 2. Setup configuration
cp .env.example .env
nano .env  # Edit with your values

# 3. Place certificates
mkdir -p certs
cp /path/to/app-cert.pem certs/
cp /path/to/app-key.pem certs/

# 4. Start the service
docker-compose up -d

# 5. View logs
docker-compose logs -f
```

### Option 2: Python (Local)

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Set environment variables
export CGW_NAME="YourGatewayName"
export ROLESANYWHERE_CERTIFICATE_PATH="/path/to/app-cert.pem"
export ROLESANYWHERE_PRIVATE_KEY_PATH="/path/to/app-key.pem"
export ROLESANYWHERE_TRUST_ANCHOR_ARN="arn:aws:rolesanywhere:..."
export ROLESANYWHERE_PROFILE_ARN="arn:aws:rolesanywhere:..."
export ROLESANYWHERE_ROLE_ARN="arn:aws:iam::..."
export AWS_REGION="eu-west-1"

# 3. Run
python3 main.py
```

## Documentation

- **[IAM Roles Anywhere Setup Guide](IAM_ROLES_ANYWHERE_SETUP.md)** - Complete step-by-step guide to set up IAM Roles Anywhere authentication
- **[Quick Start Guide](QUICKSTART.md)** - Fast deployment instructions for all platforms
- **[Docker Swarm Deployment](DOCKER_SWARM_DEPLOYMENT.md)** - Deploy to Docker Swarm clusters
- **[CLAUDE.md](CLAUDE.md)** - Developer documentation and architecture overview

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CGW_NAME` | Name tag for Customer Gateway | `MyOffice-CGW` |
| `ROLESANYWHERE_CERTIFICATE_PATH` | Path to application certificate | `/certs/app-cert.pem` |
| `ROLESANYWHERE_PRIVATE_KEY_PATH` | Path to private key | `/certs/app-key.pem` |
| `ROLESANYWHERE_TRUST_ANCHOR_ARN` | IAM Roles Anywhere trust anchor ARN | `arn:aws:rolesanywhere:...` |
| `ROLESANYWHERE_PROFILE_ARN` | IAM Roles Anywhere profile ARN | `arn:aws:rolesanywhere:...` |
| `ROLESANYWHERE_ROLE_ARN` | IAM role ARN | `arn:aws:iam::...` |
| `AWS_REGION` | AWS region | `eu-west-1` |

### AWS Permissions Required

The IAM role needs these EC2 permissions:
- `ec2:DescribeVpnConnections`
- `ec2:DescribeCustomerGateways`
- `ec2:CreateCustomerGateway`
- `ec2:ModifyVpnConnection`
- `ec2:DeleteCustomerGateway`
- `ec2:CreateTags`

See [iam-policy.json](iam-policy.json) for the complete policy.

## Deployment Options

### Docker Compose
```bash
docker-compose up -d
```
Best for: Most users, single-host deployments

### Docker Swarm
```bash
docker stack deploy -c docker-stack.yml dynip
```
Best for: Legacy Swarm clusters, multi-host orchestration

### Docker CLI
```bash
docker run -d --name dynip-updater \
  -e CGW_NAME="..." \
  [other env vars...] \
  -v /path/to/certs:/certs:ro \
  dynip-aws-s2s-cgw-update
```
Best for: Manual control, testing

### Systemd (Python)
Create a systemd service for production Python deployments. See [QUICKSTART.md](QUICKSTART.md) for details.

## Monitoring

The application outputs detailed logs:

```
[2025-11-11 13:15:00] Starting IP check...
  Found VPN connection with Customer Gateway ID: cgw-xxxxx
  Current CGW IP in AWS: 1.2.3.4
  My public IP address: 1.2.3.4
  ✓ IPs match - no update needed
```

When an update occurs:
```
[2025-11-11 13:20:00] Starting IP check...
  Found VPN connection with Customer Gateway ID: cgw-xxxxx
  Current CGW IP in AWS: 1.2.3.4
  My public IP address: 5.6.7.8
  ✗ IPs differ - updating Customer Gateway...
    Created new Customer Gateway: cgw-yyyyy
    Updated VPN connection to use new Customer Gateway
    Deleted old Customer Gateway: cgw-xxxxx
  ✓ Update complete!
```

## Security Considerations

- **Certificates**: Application certificates are valid for 5 years. Set a reminder to renew before expiration.
- **Private Keys**: Always use restrictive permissions (`chmod 600`) on private key files
- **Docker Secrets**: Use Docker secrets (not volumes) when deploying to Swarm
- **Read-Only Mounts**: Certificate volumes should be mounted read-only (`:ro`)
- **No Static Credentials**: This application uses IAM Roles Anywhere to avoid storing AWS credentials

## Troubleshooting

### Service won't start
- Check Docker/application logs
- Verify all environment variables are set
- Ensure certificates are readable and in the correct location

### "Untrusted certificate" error
- Certificate bundle must contain both app cert and CA cert
- Verify: `cat app-cert-only.pem ca-cert.pem > app-cert.pem`

### "Access Denied" errors
- Verify IAM role has required permissions
- Check trust policy includes `rolesanywhere.amazonaws.com`

### No VPN connection found
- Ensure you have at least one Site-to-Site VPN connection in your AWS account
- Verify IAM permissions include `ec2:DescribeVpnConnections`

See [IAM_ROLES_ANYWHERE_SETUP.md](IAM_ROLES_ANYWHERE_SETUP.md) for detailed troubleshooting.

## Contributing

This project is designed for personal/organizational use. Feel free to fork and modify for your needs.

## License

[Add your license here]

## Architecture

**Language**: Python 3.11
**Key Dependencies**: boto3, requests, schedule
**Container**: Docker with Alpine-based Python image
**Authentication**: AWS IAM Roles Anywhere with X.509 certificates
**Scheduling**: Python `schedule` library (5-minute intervals)

For detailed architecture information, see [CLAUDE.md](CLAUDE.md).