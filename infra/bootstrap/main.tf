# Bootstrap: creates the S3 bucket that holds the MAIN config's remote state.
#
# Why separate? The bucket that stores Terraform state can't be created by the
# same Terraform that stores its state there (chicken-and-egg). So this small
# config uses LOCAL state and is run once, up front. It creates an S3 bucket with
# versioning + encryption + public access blocked. State locking for the main
# config uses S3-native locking (use_lockfile), so no DynamoDB table is needed
# (Terraform >= 1.10).
#
# Usage (run once):
#   cd infra/bootstrap
#   terraform init && terraform apply
#   terraform output state_bucket_name   # plug into ../backend.tf

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
  # Bootstrap keeps LOCAL state on purpose (it has nowhere remote to go yet).
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "Region for the state bucket. Keep it the same as the main config."
  type        = string
  default     = "us-east-1"
}

data "aws_caller_identity" "current" {}

locals {
  # Globally-unique, deterministic bucket name from account + region.
  state_bucket_name = "agent-memory-lab-tfstate-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
}

resource "aws_s3_bucket" "tfstate" {
  bucket = local.state_bucket_name
  tags = {
    Project = "agent-memory-lab"
    Purpose = "terraform-remote-state"
  }
}

# Versioning: keep history of state so a bad apply can be recovered.
resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Encrypt state at rest (it can contain sensitive values).
resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block all public access — state must never be public.
resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "state_bucket_name" {
  description = "Name of the S3 bucket for remote state. Use this in ../backend.tf."
  value       = aws_s3_bucket.tfstate.id
}

output "state_region" {
  value = var.aws_region
}
