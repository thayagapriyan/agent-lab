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

# Newer Claude models are invoked through a cross-region inference profile (id with
# a "us." prefix). Invoking a profile requires permission on BOTH the inference
# profile ARN and the underlying foundation models it can route to (in any region
# the profile spans). For a learning lab we scope to the configured model family
# across regions; tighten if needed.
locals {
  is_inference_profile = startswith(var.bedrock_model_id, "us.") || startswith(var.bedrock_model_id, "global.")
  # Strip the "us." / "global." prefix to get the underlying foundation-model id.
  foundation_model_id = local.is_inference_profile ? join(".", slice(split(".", var.bedrock_model_id), 1, length(split(".", var.bedrock_model_id)))) : var.bedrock_model_id
}

data "aws_iam_policy_document" "bedrock_invoke" {
  statement {
    sid    = "InvokeConfiguredModel"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = local.is_inference_profile ? [
      # The inference profile itself (in this account/region)...
      "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.bedrock_model_id}",
      # ...and the underlying foundation models it routes to (any region).
      "arn:aws:bedrock:*::foundation-model/${local.foundation_model_id}",
      ] : [
      "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}",
    ]
  }
}

resource "aws_iam_role_policy" "bedrock_invoke" {
  name   = "${var.role_name}-bedrock-invoke"
  role   = aws_iam_role.agent.id
  policy = data.aws_iam_policy_document.bedrock_invoke.json
}
