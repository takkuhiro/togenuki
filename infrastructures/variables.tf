# Project Configuration
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-northeast1"
}

# Cloud SQL Configuration
variable "db_instance_name" {
  description = "Cloud SQL instance name"
  type        = string
  default     = "togenuki-db"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "togenuki"
}

variable "db_user" {
  description = "Database user name"
  type        = string
  default     = "togenuki"
}

variable "db_password" {
  description = "Database user password"
  type        = string
  sensitive   = true
}

variable "authorized_networks" {
  description = "List of authorized networks for Cloud SQL access"
  type = list(object({
    name = string
    cidr = string
  }))
  default = []
}

# ============================================
# Cloud Pub/Sub Configuration
# ============================================

variable "pubsub_topic_name" {
  description = "Pub/Sub topic name for Gmail push notifications"
  type        = string
  default     = "gmail-notifications"
}

variable "pubsub_subscription_name" {
  description = "Pub/Sub subscription name for webhook delivery"
  type        = string
  default     = "gmail-webhook-push"
}

# ============================================
# Artifact Registry Configuration
# ============================================

variable "artifact_registry_repository" {
  description = "Artifact Registry repository name"
  type        = string
  default     = "togenuki"
}

# ============================================
# Cloud Run Configuration
# ============================================

variable "cloud_run_service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "togenuki-api"
}

variable "cloud_run_image" {
  description = "Docker image for Cloud Run (initial placeholder, updated via docker push)"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"  # Public hello image as placeholder
}

# ============================================
# Google OAuth Configuration
# ============================================

variable "google_oauth_client_id" {
  description = "Google OAuth Client ID for Gmail API"
  type        = string
}

variable "google_oauth_client_secret" {
  description = "Google OAuth Client Secret for Gmail API"
  type        = string
  sensitive   = true
}

variable "google_oauth_redirect_uri" {
  description = "Google OAuth redirect URI"
  type        = string
  default     = "http://localhost:3000/auth/gmail/callback"
}

# ============================================
# Cloud Storage Configuration
# ============================================

variable "gcs_audio_bucket_name" {
  description = "GCS bucket name for audio files"
  type        = string
}

# ============================================
# Gemini API Configuration
# ============================================

variable "gemini_api_key" {
  description = "Gemini API key for gyaru conversion"
  type        = string
  sensitive   = true
}
