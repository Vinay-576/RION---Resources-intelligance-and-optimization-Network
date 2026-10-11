output "frontend_bucket_name" {
  value       = aws_s3_bucket.frontend.bucket
  description = "Upload the built Vite frontend here; CloudFront reads it through OAC."
}

output "model_bucket_name" {
  value       = aws_s3_bucket.models.bucket
  description = "Upload versioned RION detector and classifier weights under models/."
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.api.repository_url
  description = "Private registry for the RION backend image."
}

output "cloudfront_domain_name" {
  value       = aws_cloudfront_distribution.app.domain_name
  description = "CloudFront edge hostname for RION."
}

output "api_alb_dns_name" {
  value       = aws_lb.api.dns_name
  description = "ALB origin; its security group permits CloudFront origin-facing traffic only."
}

output "rds_endpoint" {
  value       = aws_db_instance.policy.address
  description = "Private PostgreSQL endpoint; not reachable from the public internet."
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.rion.name
}

output "ecs_task_definition_arn" {
  value = aws_ecs_task_definition.api.arn
}

output "ecs_private_subnet_ids" {
  value = [for subnet in aws_subnet.app : subnet.id]
}

output "ecs_security_group_id" {
  value = aws_security_group.app.id
}

output "detector_s3_version_id" {
  value       = aws_s3_object.detector.version_id
  description = "Versioned RION detector artifact uploaded by Terraform."
}

output "classifier_s3_version_id" {
  value       = aws_s3_object.classifier.version_id
  description = "Versioned RION category classifier artifact uploaded by Terraform."
}
