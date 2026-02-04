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
