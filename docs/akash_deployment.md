# Deploying AccountME Bot to Akash Network

This guide provides step-by-step instructions for deploying the AccountME Discord bot to the Akash Network, a decentralized cloud computing marketplace.

## Prerequisites

Before you begin, ensure you have the following:

1. **Docker** installed on your local machine
2. **Akash CLI** installed and configured
3. **AKT tokens** in your Akash wallet for deployment
4. **Docker Hub** account (or another container registry)

## Step 1: Build the Docker Image

First, build the Docker image for the bot:

```bash
# Navigate to the project root directory
cd /path/to/accountME

# Build the Docker image
docker build -t yourusername/accountme-bot:latest .
```

## Step 2: Push the Docker Image to a Registry

Push the built image to Docker Hub or another container registry:

```bash
# Log in to Docker Hub
docker login

# Push the image
docker push yourusername/accountme-bot:latest
```

## Step 3: Update the Deployment Manifest

Edit the `deploy.yaml` file to use your Docker image:

```yaml
services:
  discord-bot:
    image: yourusername/accountme-bot:latest
    # Rest of the configuration remains the same
```

## Step 4: Create a Deployment on Akash

```bash
# Create a certificate if you don't have one
akash tx cert create client --from=your-key-name

# Create the deployment
akash tx deployment create deploy.yaml --from=your-key-name --node=https://rpc.akash.forbole.com:443 --chain-id=akashnet-2 --gas=auto --gas-adjustment=1.3

# View your deployments
akash query deployment list --owner $(akash keys show your-key-name -a) --node=https://rpc.akash.forbole.com:443 --chain-id=akashnet-2
```

## Step 5: Create a Lease

After creating the deployment, you'll need to select a provider and create a lease:

```bash
# Get the deployment ID
DEPLOYMENT_ID=$(akash query deployment list --owner $(akash keys show your-key-name -a) --node=https://rpc.akash.forbole.com:443 --chain-id=akashnet-2 -o json | jq -r '.deployments[-1].deployment_id.dseq')

# List providers for your deployment
akash query market bid list --owner=$(akash keys show your-key-name -a) --node=https://rpc.akash.forbole.com:443 --chain-id=akashnet-2 --dseq=$DEPLOYMENT_ID

# Create a lease with a selected provider
akash tx market lease create --dseq=$DEPLOYMENT_ID --provider=<provider-address> --from=your-key-name --node=https://rpc.akash.forbole.com:443 --chain-id=akashnet-2 --gas=auto --gas-adjustment=1.3
```

## Step 6: Send the Manifest

After creating the lease, send the manifest to the provider:

```bash
akash provider send-manifest deploy.yaml --dseq=$DEPLOYMENT_ID --provider=<provider-address> --from=your-key-name --node=https://rpc.akash.forbole.com:443 --chain-id=akashnet-2
```

## Step 7: Verify Deployment

Check the status of your deployment:

```bash
akash provider lease-status --dseq=$DEPLOYMENT_ID --provider=<provider-address> --from=your-key-name --node=https://rpc.akash.forbole.com:443 --chain-id=akashnet-2
```

## Environment Variables

The following environment variables need to be set in your Akash deployment:

| Variable | Description |
|----------|-------------|
| DISCORD_TOKEN | Your Discord bot token |
| COMMAND_PREFIX | Prefix for bot commands (default: !) |
| DATABASE_PATH | Path to the database file (default: /data/database.db) |
| REPORTS_DIR | Directory for storing reports (default: /data/reports) |
| LOG_LEVEL | Logging level (default: INFO) |
| ADMIN_USER_IDS | Comma-separated list of Discord user IDs with admin privileges |
| XAI_API_KEY | API key for X.AI Grok Vision API |
| BACKUP_CHANNEL_ID | Discord channel ID for backups |
| BACKUP_INTERVAL_HOURS | Interval for automated backups (in hours) |
| BACKUP_RETENTION_DAYS | Number of days to retain backups |
| HEALTH_CHECK_INTERVAL_MINUTES | Interval for health checks (in minutes) |
| ERROR_THRESHOLD | Threshold for error rate alerting |
| ADMIN_NOTIFICATION_CHANNEL_ID | Discord channel ID for admin notifications |
| BACKUP_CLOUD_PROVIDER | Cloud provider for backups (discord, google, onedrive) |
| BACKUP_COMPRESSION_LEVEL | Compression level for backups (1-9) |
| BACKUP_VERIFY_INTEGRITY | Whether to verify backup integrity (true/false) |
| BACKUP_ROTATION_SCHEME | Backup rotation scheme (gfs, simple) |
| BACKUP_ENCRYPTION_KEY | Encryption key for backups |
| SENTRY_DSN | Sentry DSN for error tracking |
| GOOGLE_API_KEY | Google API key for various integrations |

## Persistent Storage

The deployment is configured with a 5GB persistent storage volume mounted at `/data`. This volume stores:

1. The SQLite database file
2. Generated reports
3. Backup files
4. Log files

## Monitoring and Logging

The bot includes built-in monitoring and health check capabilities:

1. **System Monitoring**: The bot monitors system resources and reports issues to the admin notification channel.
2. **Error Tracking**: Errors are logged and can be sent to Sentry if configured.
3. **Health Checks**: Regular health checks ensure the bot is functioning properly.
4. **Logs**: Logs are stored in the persistent volume and can be accessed via the Akash provider's web interface.

## Updating the Deployment

To update your deployment:

1. Build and push a new Docker image with a new tag
2. Update the `deploy.yaml` file with the new image tag
3. Update the deployment on Akash:

```bash
akash tx deployment update deploy.yaml --dseq=$DEPLOYMENT_ID --from=your-key-name --node=https://rpc.akash.forbole.com:443 --chain-id=akashnet-2 --gas=auto --gas-adjustment=1.3
```

## Troubleshooting

If you encounter issues with your deployment:

1. Check the logs via the Akash provider's web interface
2. Verify that all required environment variables are set correctly
3. Ensure the bot has the necessary permissions in your Discord server
4. Check the Akash deployment status and provider lease status