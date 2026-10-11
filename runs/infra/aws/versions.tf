terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# CloudFront-scoped WAF ACLs and CloudFront TLS certificates live in us-east-1.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
