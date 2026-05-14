# modules/gke/cluster/main.tf
# GKE Cluster for high-compute GenAI pipeline services

resource "google_container_cluster" "primary" {
  name     = "${var.prefix}-gke-cluster"
  project  = var.project_id
  location = var.region

  # We manage node pools separately
  remove_default_node_pool = true
  initial_node_count       = 1

  # Network configuration
  network    = var.vpc_network
  subnetwork = var.vpc_subnetwork

  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = var.master_ipv4_cidr_block
  }

  # IP allocation policy for VPC-native cluster
  ip_allocation_policy {
    cluster_secondary_range_name  = var.pods_range_name
    services_secondary_range_name = var.services_range_name
  }

  # Master authorized networks
  master_authorized_networks_config {
    dynamic "cidr_blocks" {
      for_each = var.master_authorized_networks
      content {
        cidr_block   = cidr_blocks.value.cidr_block
        display_name = cidr_blocks.value.display_name
      }
    }
  }

  # Workload Identity for secure GCP service access
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Release channel for automatic upgrades
  release_channel {
    channel = var.release_channel
  }

  # Cluster addons
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
    gce_persistent_disk_csi_driver_config {
      enabled = true
    }
  }

  # Logging and monitoring
  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }

  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]
    managed_prometheus {
      enabled = true
    }
  }

  # Maintenance window (Sunday 2-6 AM)
  maintenance_policy {
    recurring_window {
      start_time = "2024-01-01T02:00:00Z"
      end_time   = "2024-01-01T06:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SU"
    }
  }

  # Binary authorization
  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }

  # Resource labels
  resource_labels = var.labels

  # Deletion protection
  deletion_protection = var.deletion_protection

  lifecycle {
    ignore_changes = [
      node_config,
      initial_node_count,
    ]
  }
}

# On-demand node pool for baseline capacity
resource "google_container_node_pool" "on_demand" {
  name       = "${var.prefix}-on-demand-pool"
  project    = var.project_id
  location   = var.region
  cluster    = google_container_cluster.primary.name

  initial_node_count = var.on_demand_min_nodes

  autoscaling {
    min_node_count  = var.on_demand_min_nodes
    max_node_count  = var.on_demand_max_nodes
    location_policy = "BALANCED"
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = var.on_demand_machine_type
    disk_size_gb = var.node_disk_size_gb
    disk_type    = "pd-ssd"

    # Use Container-Optimized OS
    image_type = "COS_CONTAINERD"

    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # Workload Identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    # Shielded instance config
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    # Labels
    labels = merge(var.labels, {
      pool-type = "on-demand"
    })

    # Taints for workload scheduling
    taint {
      key    = "pool-type"
      value  = "on-demand"
      effect = "NO_SCHEDULE"
    }

    tags = ["gke-node", "${var.prefix}-gke"]
  }

  lifecycle {
    ignore_changes = [
      initial_node_count,
    ]
  }
}

# Spot node pool for cost-effective burst capacity
resource "google_container_node_pool" "spot" {
  name       = "${var.prefix}-spot-pool"
  project    = var.project_id
  location   = var.region
  cluster    = google_container_cluster.primary.name

  initial_node_count = var.spot_min_nodes

  autoscaling {
    min_node_count  = var.spot_min_nodes
    max_node_count  = var.spot_max_nodes
    location_policy = "ANY"
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = var.spot_machine_type
    disk_size_gb = var.node_disk_size_gb
    disk_type    = "pd-ssd"

    # Spot VM configuration
    spot = true

    # Use Container-Optimized OS
    image_type = "COS_CONTAINERD"

    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # Workload Identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    # Shielded instance config
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    # Labels
    labels = merge(var.labels, {
      pool-type = "spot"
    })

    # Taints - workloads must tolerate spot
    taint {
      key    = "cloud.google.com/gke-spot"
      value  = "true"
      effect = "NO_SCHEDULE"
    }

    tags = ["gke-node", "${var.prefix}-gke", "spot"]
  }

  lifecycle {
    ignore_changes = [
      initial_node_count,
    ]
  }
}
