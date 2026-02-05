terraform {
  required_version = ">= 1.0.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud SQL PostgreSQL Instance (minimal for hackathon)
resource "google_sql_database_instance" "togenuki" {
  name             = var.db_instance_name
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier      = "db-f1-micro"
    disk_size = 10
    disk_type = "PD_HDD"

    ip_configuration {
      ipv4_enabled = true

      dynamic "authorized_networks" {
        for_each = var.authorized_networks
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.cidr
        }
      }
    }
  }

  deletion_protection = false
}

# Database
resource "google_sql_database" "togenuki" {
  name     = var.db_name
  instance = google_sql_database_instance.togenuki.name
}

# Database User
resource "google_sql_user" "togenuki" {
  name     = var.db_user
  instance = google_sql_database_instance.togenuki.name
  password = var.db_password
}

# ============================================
# Cloud Pub/Sub (Gmail Push Notifications)
# ============================================

# Pub/Sub Topic for Gmail notifications
resource "google_pubsub_topic" "gmail_notifications" {
  name = var.pubsub_topic_name

  labels = {
    purpose = "gmail-push-notifications"
    app     = "togenuki"
  }
}

# Grant Gmail API service account publisher access to the topic
# This allows Gmail to publish notifications to our topic
resource "google_pubsub_topic_iam_member" "gmail_publisher" {
  topic  = google_pubsub_topic.gmail_notifications.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:gmail-api-push@system.gserviceaccount.com"
}

# Pub/Sub Subscription (Push to Cloud Run webhook)
resource "google_pubsub_subscription" "gmail_push" {
  name  = var.pubsub_subscription_name
  topic = google_pubsub_topic.gmail_notifications.id

  # Push configuration for webhook delivery
  push_config {
    push_endpoint = "${google_cloud_run_v2_service.api.uri}/api/webhook/gmail"
  }

  # Acknowledgement deadline (seconds)
  ack_deadline_seconds = 20

  # Retry policy
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  # Message retention (7 days)
  message_retention_duration = "604800s"

  # Expiration policy (never expire)
  expiration_policy {
    ttl = ""
  }

  labels = {
    purpose = "gmail-webhook"
    app     = "togenuki"
  }

  depends_on = [google_cloud_run_v2_service.api]
}

# ============================================
# Artifact Registry
# ============================================

resource "google_artifact_registry_repository" "api" {
  location      = var.region
  repository_id = var.artifact_registry_repository
  format        = "DOCKER"

  labels = {
    app = "togenuki"
  }
}

# ============================================
# Cloud Run (Backend API)
# ============================================

# Cloud Run Service
resource "google_cloud_run_v2_service" "api" {
  name     = var.cloud_run_service_name
  location = var.region

  template {
    containers {
      # Initial image - will be updated via gcloud command
      image = var.cloud_run_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      # Environment variables
      env {
        name  = "DEBUG"
        value = "false"
      }

      env {
        name  = "DATABASE_URL"
        value = "postgresql+asyncpg://${var.db_user}:${var.db_password}@/${var.db_name}?host=/cloudsql/${google_sql_database_instance.togenuki.connection_name}"
      }

      env {
        name  = "GOOGLE_CLIENT_ID"
        value = var.google_oauth_client_id
      }

      env {
        name  = "GOOGLE_CLIENT_SECRET"
        value = var.google_oauth_client_secret
      }

      env {
        name  = "GOOGLE_REDIRECT_URI"
        value = var.google_oauth_redirect_uri
      }

      env {
        name  = "FIREBASE_CREDENTIALS_PATH"
        value = "secrets/firebase-service-account.json"
      }

      # Cloud SQL connection
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.togenuki.connection_name]
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = {
    app = "togenuki"
  }

  lifecycle {
    # Ignore image changes - managed by gcloud command
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }
}

# Allow unauthenticated access to Cloud Run
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
