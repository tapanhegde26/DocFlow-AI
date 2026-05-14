# modules/gke/cluster/variables.tf

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "vpc_network" {
  description = "VPC network self link"
  type        = string
}

variable "vpc_subnetwork" {
  description = "VPC subnetwork self link"
  type        = string
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for GKE master"
  type        = string
  default     = "172.16.0.0/28"
}

variable "pods_range_name" {
  description = "Name of the secondary range for pods"
  type        = string
  default     = ""
}

variable "services_range_name" {
  description = "Name of the secondary range for services"
  type        = string
  default     = ""
}

variable "master_authorized_networks" {
  description = "List of authorized networks for master access"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = [
    {
      cidr_block   = "10.0.0.0/8"
      display_name = "Internal VPC"
    }
  ]
}

variable "release_channel" {
  description = "GKE release channel"
  type        = string
  default     = "REGULAR"
}

# On-demand node pool configuration
variable "on_demand_machine_type" {
  description = "Machine type for on-demand nodes"
  type        = string
  default     = "e2-standard-4"
}

variable "on_demand_min_nodes" {
  description = "Minimum number of on-demand nodes"
  type        = number
  default     = 2
}

variable "on_demand_max_nodes" {
  description = "Maximum number of on-demand nodes"
  type        = number
  default     = 4
}

# Spot node pool configuration
variable "spot_machine_type" {
  description = "Machine type for spot nodes"
  type        = string
  default     = "e2-standard-4"
}

variable "spot_min_nodes" {
  description = "Minimum number of spot nodes"
  type        = number
  default     = 0
}

variable "spot_max_nodes" {
  description = "Maximum number of spot nodes"
  type        = number
  default     = 4
}

variable "node_disk_size_gb" {
  description = "Disk size for nodes in GB"
  type        = number
  default     = 50
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}
