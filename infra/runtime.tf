# AgentCore Runtime deployable (Iteration 6): ECR repo + runtime + execution role.
#
# Flat, not a module: this lab has ONE agent, so the sibling's reusable
# `modules/agent/` (5 agents) would be a single-implementation abstraction here.
# Resource bodies mirror the sibling's module (ECR + agentcore_trust role + runtime)
# so the wiring is the same; only the memory IAM (below) is extra — the sibling's
# researcher path doesn't use AgentCore Memory, this lab's whole point is that it does.
#
# The container exposes /ping + /invocations on 8080 (agent/runtime.py via
# BedrockAgentCoreApp). Deploy = build the Dockerfile for arm64, push to this ECR
# repo, then apply so the runtime points at the pushed image (the CI does this in
# order; see .github/workflows/deploy.yml).

resource "aws_ecr_repository" "runtime" {
  name                 = var.runtime_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "runtime" {
  repository = aws_ecr_repository.runtime.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only 10 most recent images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 }
      action       = { type = "expire" }
    }]
  })
}

# Trust policy — AgentCore Runtime assumes this role. SourceAccount condition so only
# our account's runtime can assume it (mirrors the sibling).
data "aws_iam_policy_document" "runtime_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "runtime" {
  name               = "${var.runtime_name}-runtime"
  assume_role_policy = data.aws_iam_policy_document.runtime_trust.json
  tags               = { Project = "agent-memory-lab" }
}

# Pull the image from ECR.
resource "aws_iam_role_policy" "runtime_ecr_pull" {
  name = "${var.runtime_name}-ecr-pull"
  role = aws_iam_role.runtime.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
      ]
      Resource = "*"
    }]
  })
}

# Write CloudWatch logs (so deployed runs are visible — Iter 6 DoD).
resource "aws_iam_role_policy" "runtime_logs" {
  name = "${var.runtime_name}-logs"
  role = aws_iam_role.runtime.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/*"
    }]
  })
}

# Invoke the Bedrock model. Same inference-profile reasoning as iam.tf (locals there).
resource "aws_iam_role_policy" "runtime_bedrock_invoke" {
  name = "${var.runtime_name}-bedrock-invoke"
  role = aws_iam_role.runtime.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
      Resource = local.is_inference_profile ? [
        "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.bedrock_model_id}",
        "arn:aws:bedrock:*::foundation-model/${local.foundation_model_id}",
        ] : [
        "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}",
      ]
    }]
  })
}

# AgentCore Memory access — the deployed agent reads/writes the lab's memory store
# (the session manager calls create_event / retrieve_memories / list_events etc.).
# Scoped to this lab's memory resource. This is the extra the sibling doesn't have.
resource "aws_iam_role_policy" "runtime_memory" {
  name = "${var.runtime_name}-memory"
  role = aws_iam_role.runtime.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "bedrock-agentcore:CreateEvent",
        "bedrock-agentcore:GetEvent",
        "bedrock-agentcore:ListEvents",
        "bedrock-agentcore:DeleteEvent",
        "bedrock-agentcore:RetrieveMemoryRecords",
      ]
      Resource = [
        aws_bedrockagentcore_memory.lab.arn,
        "${aws_bedrockagentcore_memory.lab.arn}/*",
      ]
    }]
  })
}

# The runtime itself. A DEFAULT endpoint is created automatically, so
# invoke-agent-runtime works against the ARN without a separate endpoint resource.
# MEMORY_ID / MEMORY_NAMESPACE / BEDROCK_MODEL_ID are passed as env vars so the
# deployed container reads the same config the local agent does (no code change).
resource "aws_bedrockagentcore_agent_runtime" "agent" {
  agent_runtime_name = replace(var.runtime_name, "-", "_")
  description        = "Agent Memory Lab — the Strands agent served on AgentCore Runtime."
  role_arn           = aws_iam_role.runtime.arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.runtime.repository_url}:${var.image_tag}"
    }
  }

  network_configuration {
    network_mode = "PUBLIC"
  }

  protocol_configuration {
    server_protocol = "HTTP"
  }

  environment_variables = {
    BEDROCK_MODEL_ID = var.bedrock_model_id
    MEMORY_ID        = aws_bedrockagentcore_memory.lab.id
    MEMORY_NAMESPACE = var.memory_namespace
  }

  depends_on = [
    aws_iam_role_policy.runtime_ecr_pull,
    aws_iam_role_policy.runtime_logs,
    aws_iam_role_policy.runtime_bedrock_invoke,
    aws_iam_role_policy.runtime_memory,
  ]
}
