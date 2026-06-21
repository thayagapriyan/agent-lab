# Agent Memory Lab — infrastructure (Terraform)
#
# Iteration 1 scope: Bedrock access only. This provisions an IAM role + policy
# that grants permission to invoke the chosen Bedrock model, and surfaces the
# current account/region so you can verify access. The AgentCore Memory resource,
# ECR, and Runtime come in their own iterations (2 and 6).
#
# State is local for this learning lab (see .gitignore). Move to a remote backend
# if this ever needs to be shared.

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Identity / region — handy for verification and for scoping ARNs.
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
