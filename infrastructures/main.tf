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
