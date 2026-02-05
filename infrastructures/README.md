# TogeNuki Infrastructure

Terraform configuration for TogeNuki GCP infrastructure.

## Resources

- **Cloud SQL**: PostgreSQL database
- **Cloud Run**: Backend API service
- **Cloud Pub/Sub**: Gmail push notification handling
- **Artifact Registry**: Docker image repository

## Prerequisites

1. [Terraform](https://www.terraform.io/downloads) >= 1.0.0
2. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
3. GCP Project with billing enabled

## Setup

### 1. Authenticate with GCP

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable required APIs

```bash
gcloud services enable sqladmin.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### 3. Create terraform.tfvars

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# Required
project_id                 = "your-project-id"
db_password                = "your-secure-password"
google_oauth_client_id     = "your-client-id.apps.googleusercontent.com"
google_oauth_client_secret = "your-client-secret"

# Optional (has defaults)
google_oauth_redirect_uri  = "https://your-frontend.web.app/auth/gmail/callback"
```

### 4. Initialize and Apply

```bash
terraform init
terraform plan
terraform apply
```

## Outputs

After successful apply:

| Output | Description |
|--------|-------------|
| `cloud_run_url` | Backend API URL |
| `webhook_url` | Gmail Pub/Sub webhook URL |
| `gmail_watch_topic` | Topic for Gmail API users.watch() |
| `docker_image_url` | Artifact Registry image URL for docker push |
| `db_instance_connection_name` | Cloud SQL connection name |

## Deploy Backend API Image

After Terraform creates the Cloud Run service (with placeholder image), deploy your actual API:

```bash
cd ../apps/api
./deploy.sh
```

This script:
1. Configures Docker authentication for Artifact Registry
2. Builds Docker image locally
3. Pushes to Artifact Registry
4. Updates Cloud Run service with new image

## Gmail Watch Setup

After deployment, set up Gmail push notifications:

```bash
# Get the topic name
terraform output gmail_watch_topic

# Use Gmail API to watch inbox (via your application or API Explorer)
# Topic: projects/YOUR_PROJECT/topics/gmail-notifications
```

## Connect to Database

### From local machine

1. Add your IP to `authorized_networks` in terraform.tfvars
2. Run `terraform apply`
3. Connect:

```bash
psql "postgresql://togenuki:PASSWORD@$(terraform output -raw db_public_ip):5432/togenuki"
```

### From Cloud Run

Automatically configured via Cloud SQL Proxy (Unix socket).

## Development vs Production

| Setting | Development | Production |
|---------|-------------|------------|
| `db_tier` | db-f1-micro | db-custom-2-4096+ |
| `min_instances` | 0 | 1+ |
| `deletion_protection` | false | true |

## Cost Estimate (Development)

- Cloud SQL (db-f1-micro): ~$8/month
- Cloud Run: Pay per use (~$0 at low traffic)
- Pub/Sub: ~$0 (free tier)
- **Total**: ~$8-10/month

## Clean Up

```bash
terraform destroy
```
