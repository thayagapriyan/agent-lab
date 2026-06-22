output "account_id" {
  description = "The AWS account these resources live in."
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "The region in use."
  value       = data.aws_region.current.region
}

output "agent_role_arn" {
  description = "ARN of the IAM role granting Bedrock invoke permission."
  value       = aws_iam_role.agent.arn
}

output "bedrock_model_id" {
  description = "The Bedrock model the role is scoped to (also set BEDROCK_MODEL_ID to this)."
  value       = var.bedrock_model_id
}

# --- Memory (Iteration 2) ---

output "memory_id" {
  description = "AgentCore Memory resource id. Set this as MEMORY_ID in .env."
  value       = aws_bedrockagentcore_memory.lab.id
}

output "memory_arn" {
  description = "ARN of the AgentCore Memory resource."
  value       = aws_bedrockagentcore_memory.lab.arn
}

output "memory_namespace" {
  description = "Namespace the semantic strategy stores under (must match at retrieval)."
  value       = var.memory_namespace
}
