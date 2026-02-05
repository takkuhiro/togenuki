# Cloud SQL Outputs
output "db_instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.togenuki.name
}

output "db_instance_connection_name" {
  description = "Cloud SQL instance connection name (for Cloud Run)"
  value       = google_sql_database_instance.togenuki.connection_name
}

output "db_public_ip" {
  description = "Cloud SQL public IP address"
  value       = google_sql_database_instance.togenuki.public_ip_address
}

output "db_name" {
  description = "Database name"
  value       = google_sql_database.togenuki.name
}

output "db_user" {
  description = "Database user name"
  value       = google_sql_user.togenuki.name
}

output "database_url" {
  description = "PostgreSQL connection URL (without password)"
  value       = "postgresql://${google_sql_user.togenuki.name}@${google_sql_database_instance.togenuki.public_ip_address}:5432/${google_sql_database.togenuki.name}"
  sensitive   = false
}

output "database_url_template" {
  description = "PostgreSQL connection URL template (replace PASSWORD)"
  value       = "postgresql://${google_sql_user.togenuki.name}:PASSWORD@${google_sql_database_instance.togenuki.public_ip_address}:5432/${google_sql_database.togenuki.name}"
}

# ============================================
# Cloud Pub/Sub Outputs
# ============================================

output "pubsub_topic_name" {
  description = "Pub/Sub topic name for Gmail notifications"
  value       = google_pubsub_topic.gmail_notifications.name
}

output "pubsub_topic_id" {
  description = "Pub/Sub topic ID (full resource path)"
  value       = google_pubsub_topic.gmail_notifications.id
}

output "pubsub_subscription_name" {
  description = "Pub/Sub subscription name"
  value       = google_pubsub_subscription.gmail_push.name
}

output "gmail_watch_topic" {
  description = "Topic name for Gmail API users.watch() call"
  value       = "projects/${var.project_id}/topics/${google_pubsub_topic.gmail_notifications.name}"
}

# ============================================
# Artifact Registry Outputs
# ============================================

output "artifact_registry_repository" {
  description = "Artifact Registry repository name"
  value       = google_artifact_registry_repository.api.name
}

output "docker_image_url" {
  description = "Docker image URL for pushing (use with :tag)"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.api.name}/${var.cloud_run_service_name}"
}

# ============================================
# Cloud Run Outputs
# ============================================

output "cloud_run_service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.api.name
}

output "cloud_run_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.api.uri
}

output "webhook_url" {
  description = "Gmail webhook URL for Pub/Sub"
  value       = "${google_cloud_run_v2_service.api.uri}/api/webhook/gmail"
}
