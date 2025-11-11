# Docker Swarm Deployment Guide

This guide covers deploying the dynip-aws-s2s-cgw-update application to a Docker Swarm cluster.

## Prerequisites

- Docker Swarm initialized and running
- Access to a manager node
- Certificates generated (app-cert.pem and app-key.pem)
- Environment variables configured

## Key Differences from Docker Compose

1. **No `env_file` support**: Environment variables must be exported or passed differently
2. **No `build` directive**: Image must be built separately and available in registry or on nodes
3. **Secrets vs Volumes**: Swarm secrets are more secure for sensitive files
4. **Deploy section**: Swarm-specific configuration for replicas, placement, resources

## Deployment Steps

### Step 1: Build and Make Image Available

**Option A: Build on each node** (simple for single/few nodes):
```bash
# On each swarm node, or at least the node where it will run
docker build -t dynip-aws-s2s-cgw-update:latest .
```

**Option B: Use a registry** (better for multi-node clusters):
```bash
# Build and tag
docker build -t your-registry.com/dynip-aws-s2s-cgw-update:latest .

# Push to registry
docker push your-registry.com/dynip-aws-s2s-cgw-update:latest

# Update docker-stack.yml to use your registry image
```

### Step 2: Create Docker Secrets

Docker Swarm secrets are the secure way to handle certificates:

```bash
# Create secrets from certificate files
docker secret create dynip_app_cert app-cert.pem
docker secret create dynip_app_key app-key.pem

# Verify secrets were created
docker secret ls
```

**Important**: Once created, secrets cannot be updated. To update:
```bash
# Remove the old secret (will require redeploying the stack)
docker secret rm dynip_app_cert
docker secret rm dynip_app_key

# Create new secrets
docker secret create dynip_app_cert app-cert.pem
docker secret create dynip_app_key app-key.pem

# Redeploy the stack
```

### Step 3: Set Environment Variables

Swarm doesn't support `.env` files with `docker stack deploy`. You must export variables:

```bash
export CGW_NAME="YourGatewayName"
export ROLESANYWHERE_TRUST_ANCHOR_ARN="arn:aws:rolesanywhere:eu-west-1:123456789012:trust-anchor/xxx"
export ROLESANYWHERE_PROFILE_ARN="arn:aws:rolesanywhere:eu-west-1:123456789012:profile/xxx"
export ROLESANYWHERE_ROLE_ARN="arn:aws:iam::123456789012:role/dynip-cgw-updater-role"
export AWS_REGION="eu-west-1"
```

**Alternative**: Create a shell script to source:
```bash
# Create deploy-env.sh
cat > deploy-env.sh <<'EOF'
export CGW_NAME="YourGatewayName"
export ROLESANYWHERE_TRUST_ANCHOR_ARN="arn:aws:rolesanywhere:eu-west-1:123456789012:trust-anchor/xxx"
export ROLESANYWHERE_PROFILE_ARN="arn:aws:rolesanywhere:eu-west-1:123456789012:profile/xxx"
export ROLESANYWHERE_ROLE_ARN="arn:aws:iam::123456789012:role/dynip-cgw-updater-role"
export AWS_REGION="eu-west-1"
EOF

# Source it before deploying
source deploy-env.sh
```

### Step 4: Deploy the Stack

```bash
# Deploy the stack
docker stack deploy -c docker-stack.yml dynip

# Verify deployment
docker stack ps dynip

# Check service status
docker service ls
```

### Step 5: View Logs

```bash
# Follow logs for the service
docker service logs -f dynip_dynip-updater

# View logs from specific task
docker service ps dynip_dynip-updater
docker logs <task-id>
```

## Management Commands

**Update the stack** (after config changes):
```bash
source deploy-env.sh  # If using the env script
docker stack deploy -c docker-stack.yml dynip
```

**Remove the stack**:
```bash
docker stack rm dynip
```

**Scale the service** (not recommended for this app - should be 1 replica):
```bash
docker service scale dynip_dynip-updater=1
```

**Inspect the service**:
```bash
docker service inspect dynip_dynip-updater
```

**View service events**:
```bash
docker service ps dynip_dynip-updater
```

## Troubleshooting

### Service won't start
```bash
# Check service logs
docker service logs dynip_dynip-updater

# Check service status and error messages
docker service ps dynip_dynip-updater --no-trunc
```

### "image not found" error
- Ensure the image is built on the node where the service is scheduled
- Or use a registry and update the image name in docker-stack.yml

### "secret not found" error
```bash
# Verify secrets exist
docker secret ls

# Recreate if necessary
docker secret create dynip_app_cert app-cert.pem
docker secret create dynip_app_key app-key.pem
```

### Environment variables not set
- Ensure variables are exported in your current shell
- Verify with: `echo $CGW_NAME`
- Re-export and redeploy if needed

### Service keeps restarting
```bash
# Check logs for errors
docker service logs dynip_dynip-updater

# Common issues:
# - Invalid IAM Roles Anywhere configuration
# - Missing or invalid certificates
# - No VPN connections found in AWS
```

## Placement Constraints

The default `docker-stack.yml` constrains to manager nodes. To change this:

**Run on any node**:
```yaml
deploy:
  placement:
    constraints: []
```

**Run on specific node**:
```yaml
deploy:
  placement:
    constraints:
      - node.hostname == your-node-name
```

**Run on worker nodes only**:
```yaml
deploy:
  placement:
    constraints:
      - node.role == worker
```

## Alternative: Using Config Instead of Secrets

If you prefer using Docker configs (less secure but more flexible):

```bash
# Create configs
docker config create dynip_app_cert app-cert.pem
docker config create dynip_app_key app-key.pem

# Update docker-stack.yml to use configs instead of secrets
configs:
  app_cert:
    external: true
    name: dynip_app_cert
  app_key:
    external: true
    name: dynip_app_key
```

Then in the service definition:
```yaml
configs:
  - source: app_cert
    target: /certs/app-cert.pem
  - source: app_key
    target: /certs/app-key.pem
```

**Note**: Configs are stored unencrypted in the Raft log, so secrets are preferred for sensitive data.

## Migration from Swarm to Docker Compose

When you're ready to migrate away from Swarm:

1. Stop the stack: `docker stack rm dynip`
2. Leave swarm mode (if desired): `docker swarm leave --force`
3. Use the regular `docker-compose.yml` file
4. Deploy with: `docker-compose up -d`
