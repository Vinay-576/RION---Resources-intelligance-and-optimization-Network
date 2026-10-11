variable "aws_region" {
  description = "Region for the RION API, ALB, S3, and PostgreSQL resources."
  type        = string
  default     = "ap-south-1"
}

variable "app_domain_name" {
  description = "Public frontend domain on the CloudFront distribution, for example rion.example.com."
  type        = string
}

variable "api_domain_name" {
  description = "DNS name routed to the ALB and used for HTTPS from CloudFront to the API origin."
  type        = string
}

variable "route53_zone_name" {
  description = "Existing public Route 53 hosted zone containing both domain names."
  type        = string
}

variable "api_image_uri" {
  description = "Immutable RION API image URI in the created ECR repository, including a tag or digest."
  type        = string
}

variable "db_name" {
  type    = string
  default = "rion"
}

variable "db_username" {
  type    = string
  default = "rion_app"
}

variable "db_instance_class" {
  description = "Choose an instance class supported in the selected Region; production pilots should size from load tests."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_multi_az" {
  description = "Enable Multi-AZ for higher database availability; increases cost."
  type        = bool
  default     = false
}

variable "db_deletion_protection" {
  type    = bool
  default = true
}

variable "ecs_desired_count" {
  type    = number
  default = 1
}
