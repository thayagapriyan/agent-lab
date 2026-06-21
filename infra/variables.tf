variable "aws_region" {
  description = "AWS region for Bedrock + (later) AgentCore. Must have the services enabled."
  type        = string
  default     = "us-east-1"
}

variable "bedrock_model_id" {
  description = "Bedrock model id the agent invokes. Must be enabled in your account/region."
  type        = string
  default     = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "role_name" {
  description = "Name of the IAM role granting Bedrock invoke permission to the agent."
  type        = string
  default     = "agent-memory-lab-bedrock"
}

variable "trusted_principals" {
  description = <<-EOT
    AWS service principals allowed to assume the role. Defaults to the AgentCore
    runtime principal so the deployed agent (Iteration 6) can assume it. Adjust to
    match the actual runtime principal in your account/region — verify against
    current AWS docs.
  EOT
  type        = list(string)
  default     = ["bedrock-agentcore.amazonaws.com"]
}
