locals {
  name          = "rion"
  azs           = slice(data.aws_availability_zones.available.names, 0, 2)
  subnet_index  = { for index, az in local.azs : az => index }
  api_log_group = "/aws/ecs/rion/api"
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

data "aws_route53_zone" "public" {
  name         = var.route53_zone_name
  private_zone = false
}

resource "aws_acm_certificate" "frontend" {
  provider          = aws.us_east_1
  domain_name       = var.app_domain_name
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
  tags = { Application = local.name }
}

resource "aws_route53_record" "frontend_certificate_validation" {
  for_each = {
    for option in aws_acm_certificate.frontend.domain_validation_options : option.domain_name => {
      name   = option.resource_record_name
      type   = option.resource_record_type
      record = option.resource_record_value
    }
  }
  zone_id         = data.aws_route53_zone.public.zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 60
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "frontend" {
  provider        = aws.us_east_1
  certificate_arn = aws_acm_certificate.frontend.arn
  validation_record_fqdns = [
    for record in aws_route53_record.frontend_certificate_validation : record.fqdn
  ]
}

resource "aws_acm_certificate" "api" {
  domain_name       = var.api_domain_name
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
  tags = { Application = local.name }
}

resource "aws_route53_record" "api_certificate_validation" {
  for_each = {
    for option in aws_acm_certificate.api.domain_validation_options : option.domain_name => {
      name   = option.resource_record_name
      type   = option.resource_record_type
      record = option.resource_record_value
    }
  }
  zone_id         = data.aws_route53_zone.public.zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 60
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn = aws_acm_certificate.api.arn
  validation_record_fqdns = [
    for record in aws_route53_record.api_certificate_validation : record.fqdn
  ]
}

data "aws_ec2_managed_prefix_list" "cloudfront_origin_facing" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "random_password" "db" {
  length  = 36
  special = false
}

resource "random_password" "origin_token" {
  length  = 48
  special = false
}

resource "aws_vpc" "rion" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${local.name}-vpc" }
}

resource "aws_internet_gateway" "rion" {
  vpc_id = aws_vpc.rion.id
  tags   = { Name = "${local.name}-igw" }
}

resource "aws_subnet" "public" {
  for_each                = local.subnet_index
  vpc_id                  = aws_vpc.rion.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(aws_vpc.rion.cidr_block, 8, each.value)
  map_public_ip_on_launch = true
  tags                    = { Name = "${local.name}-public-${each.value + 1}" }
}

resource "aws_subnet" "app" {
  for_each          = local.subnet_index
  vpc_id            = aws_vpc.rion.id
  availability_zone = each.key
  cidr_block        = cidrsubnet(aws_vpc.rion.cidr_block, 8, each.value + 16)
  tags              = { Name = "${local.name}-app-${each.value + 1}" }
}

resource "aws_subnet" "database" {
  for_each          = local.subnet_index
  vpc_id            = aws_vpc.rion.id
  availability_zone = each.key
  cidr_block        = cidrsubnet(aws_vpc.rion.cidr_block, 8, each.value + 32)
  tags              = { Name = "${local.name}-db-${each.value + 1}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.rion.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.rion.id
  }
  tags = { Name = "${local.name}-public" }
}

resource "aws_route_table_association" "public" {
  for_each       = aws_subnet.public
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.rion.id
  tags   = { Name = "${local.name}-private" }
}

resource "aws_route_table_association" "app" {
  for_each       = aws_subnet.app
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "database" {
  for_each       = aws_subnet.database
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Accept TLS only from CloudFront edge locations."
  vpc_id      = aws_vpc.rion.id
  ingress {
    description     = "CloudFront origin-facing prefix list"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront_origin_facing.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${local.name}-alb" }
}

resource "aws_security_group" "app" {
  name        = "${local.name}-app"
  description = "Allow API traffic only from the application load balancer."
  vpc_id      = aws_vpc.rion.id
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${local.name}-app" }
}

resource "aws_security_group" "database" {
  name        = "${local.name}-database"
  description = "Allow PostgreSQL only from RION API tasks."
  vpc_id      = aws_vpc.rion.id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  tags = { Name = "${local.name}-database" }
}

resource "aws_security_group" "endpoints" {
  name        = "${local.name}-endpoints"
  description = "Allow private API tasks to reach interface VPC endpoints over TLS."
  vpc_id      = aws_vpc.rion.id
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  tags = { Name = "${local.name}-endpoints" }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.rion.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
  tags              = { Name = "${local.name}-s3" }
}

resource "aws_vpc_endpoint" "interface" {
  for_each            = toset(["ecr.api", "ecr.dkr", "logs", "secretsmanager"])
  vpc_id              = aws_vpc.rion.id
  service_name        = "com.amazonaws.${var.aws_region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [for subnet in aws_subnet.app : subnet.id]
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.endpoints.id]
  tags                = { Name = "${local.name}-${replace(each.key, ".", "-")}" }
}

resource "aws_s3_bucket" "frontend" {
  bucket        = "rion-web-${data.aws_caller_identity.current.account_id}-${random_id.suffix.hex}"
  force_destroy = false
  tags          = { Name = "${local.name}-web" }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket" "models" {
  bucket        = "rion-models-${data.aws_caller_identity.current.account_id}-${random_id.suffix.hex}"
  force_destroy = false
  tags          = { Name = "${local.name}-models" }
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_object" "detector" {
  bucket      = aws_s3_bucket.models.id
  key         = "models/material-yolo.pt"
  source      = "${path.module}/../../models/material-yolo.pt"
  source_hash = filesha256("${path.module}/../../models/material-yolo.pt")
  content_type = "application/octet-stream"
  depends_on  = [aws_s3_bucket_versioning.models]
}

resource "aws_s3_object" "classifier" {
  bucket      = aws_s3_bucket.models.id
  key         = "models/rion-classifier.pt"
  source      = "${path.module}/../../models/rion-classifier.pt"
  source_hash = filesha256("${path.module}/../../models/rion-classifier.pt")
  content_type = "application/octet-stream"
  depends_on  = [aws_s3_bucket_versioning.models]
}

resource "aws_s3_bucket_public_access_block" "models" {
  bucket                  = aws_s3_bucket.models.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_db_subnet_group" "rion" {
  name       = "${local.name}-db"
  subnet_ids = [for subnet in aws_subnet.database : subnet.id]
  tags       = { Name = "${local.name}-db" }
}

resource "aws_db_instance" "policy" {
  identifier                  = "${local.name}-policy-${random_id.suffix.hex}"
  engine                      = "postgres"
  instance_class              = var.db_instance_class
  allocated_storage           = 20
  max_allocated_storage       = 100
  storage_encrypted           = true
  db_name                     = var.db_name
  username                    = var.db_username
  password                    = random_password.db.result
  port                        = 5432
  db_subnet_group_name        = aws_db_subnet_group.rion.name
  vpc_security_group_ids      = [aws_security_group.database.id]
  publicly_accessible         = false
  multi_az                    = var.db_multi_az
  backup_retention_period     = 7
  auto_minor_version_upgrade  = true
  deletion_protection         = var.db_deletion_protection
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${local.name}-final-${random_id.suffix.hex}"
  copy_tags_to_snapshot       = true
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  tags                        = { Name = "${local.name}-policy-db" }
}

resource "aws_secretsmanager_secret" "runtime" {
  name                    = "/rion/runtime/${random_id.suffix.hex}"
  recovery_window_in_days = 7
  description             = "Runtime-only RION database URL and CloudFront origin verification token."
  tags                    = { Name = "${local.name}-runtime" }
}

resource "aws_secretsmanager_secret_version" "runtime" {
  secret_id = aws_secretsmanager_secret.runtime.id
  secret_string = jsonencode({
    database_url       = "postgresql+psycopg://${var.db_username}:${random_password.db.result}@${aws_db_instance.policy.address}:${aws_db_instance.policy.port}/${var.db_name}"
    origin_verify_token = random_password.origin_token.result
  })
}

resource "aws_ecr_repository" "api" {
  name                 = "rion-api"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
  tags = { Name = "${local.name}-api" }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the most recent ten immutable release images."
      selection = { tagStatus = "tagged", tagPrefixList = ["release-"], countType = "imageCountMoreThan", countNumber = 10 }
      action    = { type = "expire" }
    }]
  })
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.name}-ecs-execution-${random_id.suffix.hex}"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name               = "${local.name}-ecs-task-${random_id.suffix.hex}"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

data "aws_iam_policy_document" "task_access" {
  statement {
    sid       = "ReadVersionedModelArtifacts"
    actions   = ["s3:GetObject", "s3:GetObjectVersion"]
    resources = ["${aws_s3_bucket.models.arn}/models/*"]
  }
  statement {
    sid       = "ReadRionRuntimeSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.runtime.arn]
  }
}

resource "aws_iam_role_policy" "task_access" {
  name   = "${local.name}-runtime-access"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_access.json
}

resource "aws_cloudwatch_log_group" "api" {
  name              = local.api_log_group
  retention_in_days = 30
  tags              = { Application = local.name }
}

resource "aws_ecs_cluster" "rion" {
  name = "${local.name}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = { Name = "${local.name}-cluster" }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "4096"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name      = "rion-api"
    image     = var.api_image_uri
    essential = true
    portMappings = [{ containerPort = 8000, hostPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "APP_ENV", value = "production" },
      { name = "MODEL_PATH", value = "/app/models/material-yolo.pt" },
      { name = "CLASSIFIER_PATH", value = "/app/models/rion-classifier.pt" },
      { name = "MODEL_S3_BUCKET", value = aws_s3_bucket.models.bucket },
      { name = "MODEL_S3_KEY", value = "models/material-yolo.pt" },
      { name = "CLASSIFIER_S3_KEY", value = "models/rion-classifier.pt" },
      { name = "MODEL_SHA256", value = filesha256("${path.module}/../../models/material-yolo.pt") },
      { name = "CLASSIFIER_SHA256", value = filesha256("${path.module}/../../models/rion-classifier.pt") },
      { name = "RION_RUNTIME_SECRET_ARN", value = aws_secretsmanager_secret.runtime.arn },
      { name = "ALLOWED_HOSTS", value = "${var.api_domain_name},${aws_lb.api.dns_name},localhost,127.0.0.1" },
      { name = "FRONTEND_ORIGIN", value = "https://${var.app_domain_name}" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "api"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)\" || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 180
    }
  }])
  depends_on = [aws_iam_role_policy_attachment.execution_managed, aws_iam_role_policy.task_access, aws_s3_object.detector, aws_s3_object.classifier, aws_secretsmanager_secret_version.runtime]
  tags       = { Application = local.name }
}

resource "aws_lb" "api" {
  name               = "rion-api-${random_id.suffix.hex}"
  internal           = false
  load_balancer_type = "application"
  subnets            = [for subnet in aws_subnet.public : subnet.id]
  security_groups    = [aws_security_group.alb.id]
  drop_invalid_header_fields = true
  tags = { Name = "${local.name}-api" }
}

resource "aws_lb_target_group" "api" {
  name        = "rion-api-${random_id.suffix.hex}"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.rion.id
  health_check {
    enabled             = true
    path                = "/health"
    matcher             = "200"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  tags = { Name = "${local.name}-api" }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = aws_acm_certificate_validation.api.certificate_arn
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_ecs_service" "api" {
  name                               = "${local.name}-api"
  cluster                            = aws_ecs_cluster.rion.id
  task_definition                    = aws_ecs_task_definition.api.arn
  desired_count                      = var.ecs_desired_count
  launch_type                        = "FARGATE"
  health_check_grace_period_seconds  = 180
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  enable_execute_command             = false
  network_configuration {
    subnets          = [for subnet in aws_subnet.app : subnet.id]
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "rion-api"
    container_port   = 8000
  }
  depends_on = [aws_lb_listener.https, aws_vpc_endpoint.interface, aws_vpc_endpoint.s3]
  tags       = { Application = local.name }
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${local.name}-frontend-oac"
  description                       = "Private CloudFront access to the RION frontend bucket."
  origin_access_control_origin_type = "s3"
  signing_behavior                 = "always"
  signing_protocol                 = "sigv4"
}

resource "aws_wafv2_web_acl" "edge" {
  provider    = aws.us_east_1
  name        = "${local.name}-cloudfront-waf-${random_id.suffix.hex}"
  description = "Managed common protections and per-IP request limiting for RION."
  scope       = "CLOUDFRONT"
  default_action { allow {} }
  rule {
    name     = "AWSManagedCommonRuleSet"
    priority = 1
    override_action { none {} }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
        # Keep the managed body-size check from rejecting image uploads before
        # FastAPI applies its own request-byte and decoded-pixel limits.
        rule_action_override {
          name = "SizeRestrictions_BODY"
          action_to_use { count {} }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RIONCommonRules"
      sampled_requests_enabled   = true
    }
  }
  rule {
    name     = "PerIpRateLimit"
    priority = 2
    action { block {} }
    statement {
      rate_based_statement {
        limit              = 1200
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RIONRateLimit"
      sampled_requests_enabled   = true
    }
  }
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "RIONCloudFrontWAF"
    sampled_requests_enabled   = true
  }
  tags = { Application = local.name }
}

resource "aws_cloudfront_cache_policy" "api" {
  name        = "rion-api-no-cache-${random_id.suffix.hex}"
  min_ttl     = 0
  default_ttl = 0
  max_ttl     = 0
  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config { cookie_behavior = "none" }
    headers_config { header_behavior = "none" }
    query_strings_config { query_string_behavior = "all" }
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
  }
}

resource "aws_cloudfront_distribution" "app" {
  enabled             = true
  comment             = "RION web app and API edge"
  default_root_object = "index.html"
  aliases             = [var.app_domain_name]
  web_acl_id          = aws_wafv2_web_acl.edge.arn

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "rion-private-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
    s3_origin_config { origin_access_identity = "" }
  }

  origin {
    domain_name = var.api_domain_name
    origin_id   = "rion-api-alb"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
    custom_header {
      name  = "X-RION-Origin-Token"
      value = random_password.origin_token.result
    }
  }

  default_cache_behavior {
    target_origin_id       = "rion-private-frontend"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "rion-api-alb"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = aws_cloudfront_cache_policy.api.id
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  }

  ordered_cache_behavior {
    path_pattern           = "/health"
    target_origin_id       = "rion-api-alb"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = aws_cloudfront_cache_policy.api.id
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
      locations        = []
    }
  }
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.frontend.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
  depends_on = [aws_route53_record.api]
  tags       = { Application = local.name }
}

data "aws_iam_policy_document" "frontend_bucket" {
  statement {
    sid       = "CloudFrontReadOnly"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.app.arn]
    }
  }
  statement {
    sid       = "RequireTls"
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.frontend.arn, "${aws_s3_bucket.frontend.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    effect = "Deny"
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket     = aws_s3_bucket.frontend.id
  policy     = data.aws_iam_policy_document.frontend_bucket.json
  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

data "aws_iam_policy_document" "model_bucket_tls" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.models.arn, "${aws_s3_bucket.models.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "models" {
  bucket     = aws_s3_bucket.models.id
  policy     = data.aws_iam_policy_document.model_bucket_tls.json
  depends_on = [aws_s3_bucket_public_access_block.models]
}

resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.public.zone_id
  name    = var.api_domain_name
  type    = "A"
  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "frontend" {
  zone_id = data.aws_route53_zone.public.zone_id
  name    = var.app_domain_name
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.app.domain_name
    zone_id                = aws_cloudfront_distribution.app.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "rion-api-alb-5xx"
  alarm_description   = "More than five load balancer 5xx responses in five minutes."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_ELB_5XX_Count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  dimensions = {
    LoadBalancer = aws_lb.api.arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_cpu" {
  alarm_name          = "rion-api-high-cpu"
  alarm_description   = "Average RION ECS service CPU exceeds 85 percent."
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 85
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  dimensions = {
    ClusterName = aws_ecs_cluster.rion.name
    ServiceName = aws_ecs_service.api.name
  }
}

resource "aws_cloudwatch_dashboard" "rion" {
  dashboard_name = "RION-operations"
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6,
        properties = {
          title = "API load balancer requests and 5xx", view = "timeSeries", region = var.aws_region,
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.api.arn_suffix],
            [".", "HTTPCode_ELB_5XX_Count", ".", "."]
          ]
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6,
        properties = {
          title = "RION ECS CPU and memory", view = "timeSeries", region = var.aws_region,
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.rion.name, "ServiceName", aws_ecs_service.api.name],
            [".", "MemoryUtilization", ".", ".", ".", "."]
          ]
        }
      }
    ]
  })
}
