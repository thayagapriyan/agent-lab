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

# --- Runtime (Iteration 6) ---

variable "runtime_name" {
  description = "Name for the AgentCore Runtime + its ECR repo + IAM role (a-z, 0-9, -)."
  type        = string
  default     = "agent-memory-lab"
}

variable "image_tag" {
  description = "ECR image tag the runtime deploys. CI sets this to the git sha; defaults to latest for manual applies."
  type        = string
  default     = "latest"
}

# --- Memory (Iteration 2) ---

variable "memory_name" {
  description = "Name of the AgentCore Memory resource (unique per account; [a-zA-Z][a-zA-Z0-9_]{0,47})."
  type        = string
  default     = "agent_memory_lab"
}

variable "memory_event_expiry_days" {
  description = "Days until memory events expire (provider allows 7–365)."
  type        = number
  default     = 90

  validation {
    condition     = var.memory_event_expiry_days >= 7 && var.memory_event_expiry_days <= 365
    error_message = "memory_event_expiry_days must be between 7 and 365."
  }
}

variable "memory_namespace" {
  description = <<-EOT
    Namespace for the semantic strategy. MUST match what the agent references at
    retrieval time, or recall silently returns nothing. {actorId} is filled by
    AgentCore at runtime. Default scopes memories per actor across sessions.
  EOT
  type        = string
  default     = "semantic/{actorId}"
}
