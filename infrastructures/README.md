# TogeNuki Infrastructure

Terraform configuration for TogeNuki GCP infrastructure.

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
```

### 3. Create terraform.tfvars

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 4. Initialize Terraform

```bash
terraform init
```

### 5. Plan and Apply

```bash
# Review changes
terraform plan

# Apply changes
terraform apply
```

## Outputs

After successful apply, you'll get:

- `db_instance_connection_name`: For Cloud Run connection
- `db_public_ip`: Public IP for direct access
- `database_url_template`: Connection URL template

## Connect to Database

### From local machine

1. Add your IP to `authorized_networks` in terraform.tfvars
2. Run `terraform apply`
3. Connect using:

```bash
psql "postgresql://togenuki:PASSWORD@PUBLIC_IP:5432/togenuki"
```

### From Cloud Run

Use Cloud SQL Proxy via Unix socket:

```
/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME
```

## Development vs Production

| Setting | Development | Production |
|---------|-------------|------------|
| `db_tier` | db-f1-micro | db-custom-2-4096 or higher |
| `db_availability_type` | ZONAL | REGIONAL |
| `enable_backup` | false | true |
| `deletion_protection` | false | true |

## Clean Up

```bash
terraform destroy
```

## Cost Estimate (Development)

- db-g1-small (PostgreSQL minimum): ~$25/month
- 10GB SSD: ~$1.7/month
- Total: ~$27/month
