# IAM role + policy granting permission to invoke the Bedrock model.
#
# The agent assumes this role (locally you typically use your own credentials;
# the deployed runtime assumes the role). Scope is intentionally narrow:
# InvokeModel on the configured model only.

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = var.trusted_principals
    }
  }
}

resource "aws_iam_role" "agent" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags = {
    Project = "agent-memory-lab"
  }
}

data "aws_iam_policy_document" "bedrock_invoke" {
  statement {
    sid    = "InvokeConfiguredModel"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    # Scope to the configured model (foundation-model ARN). Broaden only if a run
    # genuinely needs more than one model.
    resources = [
      "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}",
    ]
  }
}

resource "aws_iam_role_policy" "bedrock_invoke" {
  name   = "${var.role_name}-bedrock-invoke"
  role   = aws_iam_role.agent.id
  policy = data.aws_iam_policy_document.bedrock_invoke.json
}
