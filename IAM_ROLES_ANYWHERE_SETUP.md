# IAM Roles Anywhere Setup Guide

This guide walks through setting up IAM Roles Anywhere to eliminate the need for static AWS credentials.

## Prerequisites

- AWS CLI installed and configured with admin access (for initial setup only)
- OpenSSL for certificate generation
- The IAM policy from `iam-policy.json`

## Step 1: Create a Certificate Authority (CA)

You'll need a CA to sign your certificate. For simplicity, we'll create a self-signed CA.

```bash
# Generate CA private key
openssl genrsa -out ca-key.pem 2048

# Create OpenSSL config for CA extensions
cat > ca-extensions.cnf <<'EOF'
[ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
EOF

# Generate CA certificate (valid for 10 years) with proper CA extensions
openssl req -new -x509 -days 3650 -key ca-key.pem -out ca-cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=MyCA" \
  -extensions ca -config ca-extensions.cnf

# Verify the CA certificate has correct extensions
openssl x509 -in ca-cert.pem -noout -text | grep -A 3 "Basic Constraints"
```

You should see output like:
```
Basic Constraints: critical
    CA:TRUE
```

**Important**: Keep `ca-key.pem` secure and backed up. You'll need it to sign additional certificates.

## Step 2: Create Application Certificate

```bash
# Generate application private key
openssl genrsa -out app-key.pem 2048

# Generate certificate signing request
openssl req -new -key app-key.pem -out app-csr.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=dynip-updater"

# Create OpenSSL config for certificate extensions
cat > cert-extensions.cnf <<'EOF'
[v3_req]
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF

# Sign with CA (valid for 5 years) with proper extensions
openssl x509 -req -days 1825 -in app-csr.pem \
  -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial \
  -extfile cert-extensions.cnf -extensions v3_req \
  -out app-cert-only.pem

# Create certificate bundle (app cert + CA cert chain)
# This is required for aws_signing_helper to verify the chain
cat app-cert-only.pem ca-cert.pem > app-cert.pem

# Verify certificate validity
openssl x509 -in app-cert-only.pem -noout -dates

# Verify the chain is valid
openssl verify -CAfile ca-cert.pem app-cert-only.pem
```

## Step 3: Register CA with IAM Roles Anywhere

```bash
# Create trust anchor
aws rolesanywhere create-trust-anchor \
  --name "dynip-trust-anchor" \
  --source sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData="$(cat ca-cert.pem)"} \
  --enabled

# Note the trust anchor ARN from output
```

Save the `trustAnchorArn` from the output.

**Verify registration**:
```bash
# Check the trust anchor was created with the correct certificate
aws rolesanywhere get-trust-anchor --trust-anchor-id <trust-anchor-id-from-arn>
```

**Troubleshooting**:
- If you get "Incorrect basic constraints for CA certificate" error, it means your CA certificate wasn't created with the proper extensions. You need to:
  1. Delete the incorrect certificate: `rm ca-cert.pem`
  2. Create the config file (if you skipped it): Run the `cat > ca-extensions.cnf` command from Step 1
  3. Regenerate the CA certificate using the full Step 1 commands, including the `-extensions ca -config ca-extensions.cnf` parameters
  4. Verify with: `openssl x509 -in ca-cert.pem -noout -text | grep -A 3 "Basic Constraints"`

- If you recreated the CA certificate AFTER creating the trust anchor, you must delete and recreate the trust anchor with the new CA certificate

## Step 4: Create IAM Role

```bash
# Create trust policy for Roles Anywhere
cat > trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rolesanywhere.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession",
        "sts:SetSourceIdentity"
      ]
    }
  ]
}
EOF

# Create IAM role
aws iam create-role \
  --role-name dynip-cgw-updater-role \
  --assume-role-policy-document file://trust-policy.json

# Attach permissions (using your existing iam-policy.json)
aws iam put-role-policy \
  --role-name dynip-cgw-updater-role \
  --policy-name dynip-cgw-permissions \
  --policy-document file://iam-policy.json

# Note the role ARN
aws iam get-role --role-name dynip-cgw-updater-role --query 'Role.Arn'
```

Save the role ARN from the output.

## Step 5: Create Roles Anywhere Profile

```bash
# Replace ROLE_ARN with the ARN from Step 4
aws rolesanywhere create-profile \
  --name "dynip-cgw-profile" \
  --role-arns "ROLE_ARN" \
  --enabled

# Note the profile ARN from output
```

Save the `profileArn` from the output.

## Step 6: Install AWS Signing Helper

The signing helper is AWS's official tool for IAM Roles Anywhere credential management.

```bash
# Download for Linux (adjust for your platform)
curl -LO https://rolesanywhere.amazonaws.com/releases/1.2.1/X86_64/Linux/aws_signing_helper
chmod +x aws_signing_helper
sudo mv aws_signing_helper /usr/local/bin/
```

For other platforms, see: https://docs.aws.amazon.com/rolesanywhere/latest/userguide/credential-helper.html

## Step 7: Test Credential Retrieval

```bash
# Test getting credentials (replace ARNs with your values)
aws_signing_helper credential-process \
  --certificate app-cert.pem \
  --private-key app-key.pem \
  --trust-anchor-arn arn:aws:rolesanywhere:REGION:ACCOUNT:trust-anchor/TA_ID \
  --profile-arn arn:aws:rolesanywhere:REGION:ACCOUNT:profile/PROFILE_ID \
  --role-arn arn:aws:iam::ACCOUNT:role/dynip-cgw-updater-role
```

If successful, you'll see JSON output with temporary credentials.

## Step 8: Configure Environment Variables

The modified application needs these environment variables:

```bash
export CGW_NAME="YourGatewayName"
export ROLESANYWHERE_CERTIFICATE_PATH="/path/to/app-cert.pem"
export ROLESANYWHERE_PRIVATE_KEY_PATH="/path/to/app-key.pem"
export ROLESANYWHERE_TRUST_ANCHOR_ARN="arn:aws:rolesanywhere:region:account:trust-anchor/xxx"
export ROLESANYWHERE_PROFILE_ARN="arn:aws:rolesanywhere:region:account:profile/xxx"
export ROLESANYWHERE_ROLE_ARN="arn:aws:iam::account:role/dynip-cgw-updater-role"
export AWS_REGION="us-east-1"  # Your AWS region
```

## Docker Setup

When running in Docker, mount the certificates and signing helper:

```bash
docker run \
  -e CGW_NAME="YourGatewayName" \
  -e ROLESANYWHERE_CERTIFICATE_PATH="/certs/app-cert.pem" \
  -e ROLESANYWHERE_PRIVATE_KEY_PATH="/certs/app-key.pem" \
  -e ROLESANYWHERE_TRUST_ANCHOR_ARN="arn:..." \
  -e ROLESANYWHERE_PROFILE_ARN="arn:..." \
  -e ROLESANYWHERE_ROLE_ARN="arn:..." \
  -e AWS_REGION="us-east-1" \
  -v /path/to/certs:/certs:ro \
  dynip-aws-s2s-cgw-update
```

## Security Best Practices

1. **Protect private keys**: Set restrictive permissions (`chmod 600 app-key.pem ca-key.pem`)
2. **Rotate certificates**: Set calendar reminders to renew before expiration
3. **Backup CA key**: Store `ca-key.pem` securely offline
4. **Use read-only mounts**: Mount certificates as read-only in Docker (`ro` flag)
5. **Separate CA key**: Don't deploy `ca-key.pem` with the application

## Certificate Renewal

The application certificate is valid for 5 years. When it approaches expiration:

1. Generate new CSR with the same process as Step 2
2. Sign with your CA (keeping the 5-year validity: `-days 1825`)
3. Replace `app-cert.pem` and restart the application
4. No AWS configuration changes needed (CA remains the same)

**Set a reminder**: Add a calendar reminder for 4.5 years from now to renew the certificate before expiration.

## Troubleshooting

**"Untrusted certificate" or "Insufficient certificate"**
- This means the certificate chain is incomplete
- Your `app-cert.pem` must contain BOTH the application certificate AND the CA certificate
- Recreate the bundle: `cat app-cert-only.pem ca-cert.pem > app-cert.pem`
- Verify the chain: `openssl verify -CAfile ca-cert.pem app-cert-only.pem`

**"Unable to obtain credentials"**
- Verify certificate paths are correct
- Check ARNs match your AWS resources
- Ensure IAM role trust policy includes rolesanywhere.amazonaws.com
- Verify aws_signing_helper is in PATH

**"Access Denied"**
- Check IAM policy attached to the role has required EC2 permissions
- Verify profile is associated with the correct role

**Certificate expired**
- Check certificate validity: `openssl x509 -in app-cert-only.pem -noout -dates`
- Generate and sign new certificate using CA
