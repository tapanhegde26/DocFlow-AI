# IaC-GCP/variables-hybrid.tf
# Additional variables for hybrid architecture

# GKE Configuration
variable "gke_on_demand_machine_type" {
  description = "Machine type for on-demand GKE nodes"
  type        = string
  default     = "e2-standard-4"
}

variable "gke_on_demand_min_nodes" {
  description = "Minimum number of on-demand nodes"
  type        = number
  default     = 2
}

variable "gke_on_demand_max_nodes" {
  description = "Maximum number of on-demand nodes"
  type        = number
  default     = 4
}

variable "gke_spot_machine_type" {
  description = "Machine type for spot GKE nodes"
  type        = string
  default     = "e2-standard-4"
}

variable "gke_spot_min_nodes" {
  description = "Minimum number of spot nodes"
  type        = number
  default     = 0
}

variable "gke_spot_max_nodes" {
  description = "Maximum number of spot nodes"
  type        = number
  default     = 4
}

variable "gke_node_disk_size_gb" {
  description = "Disk size for GKE nodes in GB"
  type        = number
  default     = 50
}

variable "enable_gke" {
  description = "Enable GKE cluster for high-compute services"
  type        = bool
  default     = true
}
