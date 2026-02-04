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
