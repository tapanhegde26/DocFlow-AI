# modules/vpc/outputs.tf

output "network_id" {
  description = "VPC network ID"
  value       = google_compute_network.vpc.id
}

output "network_name" {
  description = "VPC network name"
  value       = google_compute_network.vpc.name
}

output "network_self_link" {
  description = "VPC network self link"
  value       = google_compute_network.vpc.self_link
}

output "subnet_ids" {
  description = "List of subnet IDs"
  value       = google_compute_subnetwork.subnets[*].id
}

output "subnet_names" {
  description = "List of subnet names"
  value       = google_compute_subnetwork.subnets[*].name
}

output "vpc_connector_id" {
  description = "VPC connector ID for serverless services"
  value       = google_vpc_access_connector.connector.id
}

output "vpc_connector_name" {
  description = "VPC connector name"
  value       = google_vpc_access_connector.connector.name
}

output "private_ip_range_name" {
  description = "Private IP range name for service networking"
  value       = google_compute_global_address.private_ip_range.name
}

output "private_vpc_connection" {
  description = "Private VPC connection for services"
  value       = google_service_networking_connection.private_vpc_connection.id
}
