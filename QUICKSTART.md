# Quick Start Guide

## Running Locally

```bash
export CGW_NAME="YourGatewayName"
export ROLESANYWHERE_CERTIFICATE_PATH="/path/to/app-cert.pem"
export ROLESANYWHERE_PRIVATE_KEY_PATH="/path/to/app-key.pem"
export ROLESANYWHERE_TRUST_ANCHOR_ARN="arn:aws:rolesanywhere:region:account:trust-anchor/xxx"
export ROLESANYWHERE_PROFILE_ARN="arn:aws:rolesanywhere:region:account:profile/xxx"
export ROLESANYWHERE_ROLE_ARN="arn:aws:iam::account:role/dynip-cgw-updater-role"
export AWS_REGION="eu-west-1"

python3 main.py
```

## Running in Docker

### Option A: Using Docker Compose (Recommended)

1. **Setup configuration**:
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual values
nano .env  # or use your preferred editor
```

2. **Place certificates in the certs directory**:
```bash
mkdir -p certs
cp /path/to/app-cert.pem certs/
cp /path/to/app-key.pem certs/
chmod 600 certs/app-key.pem
```

3. **Start the service**:
```bash
docker-compose up -d
```

4. **View logs**:
```bash
docker-compose logs -f
```

5. **Stop the service**:
```bash
docker-compose down
```

### Option B: Using Docker CLI

**Build the image**:
```bash
docker build -t dynip-aws-s2s-cgw-update .
```

**Run the container**:
```bash
docker run -d \
  --name dynip-updater \
  -e CGW_NAME="YourGatewayName" \
  -e ROLESANYWHERE_CERTIFICATE_PATH="/certs/app-cert.pem" \
  -e ROLESANYWHERE_PRIVATE_KEY_PATH="/certs/app-key.pem" \
  -e ROLESANYWHERE_TRUST_ANCHOR_ARN="arn:aws:rolesanywhere:eu-west-1:123456789012:trust-anchor/xxx" \
  -e ROLESANYWHERE_PROFILE_ARN="arn:aws:rolesanywhere:eu-west-1:123456789012:profile/xxx" \
  -e ROLESANYWHERE_ROLE_ARN="arn:aws:iam::123456789012:role/dynip-cgw-updater-role" \
  -e AWS_REGION="eu-west-1" \
  -v /path/to/certs:/certs:ro \
  --restart unless-stopped \
  dynip-aws-s2s-cgw-update
```

**View logs**:
```bash
docker logs -f dynip-updater
```

**Stop/remove**:
```bash
docker stop dynip-updater
docker rm dynip-updater
```

## What Happens

1. App starts and fetches initial IAM Roles Anywhere credentials
2. Every 5 minutes, checks your public IP against AWS Customer Gateway IP
3. If different, creates new CGW, updates VPN connection, deletes old CGW
4. Credentials automatically refresh before expiration (every ~1 hour)

## Files You Need

Place these in a secure location (e.g., `/opt/dynip-certs/`):
- `app-cert.pem` - Your application certificate bundle
- `app-key.pem` - Your private key (chmod 600)

Do NOT deploy:
- `ca-key.pem` - Keep this offline/secure for certificate renewal only
- `ca-cert.pem` - Only needed for renewal, not runtime
