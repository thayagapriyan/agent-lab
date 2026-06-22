# CI/CD via GitHub Actions + OIDC. The deploy role here is the trust anchor the
# deploy workflow assumes; after the one-time bootstrap workflow creates it, every
# later change to this file deploys through the pipeline like any other infra.
# (Modeled on the sibling agentcore-multiagent project's infra/cicd.tf.)
#
# Bootstrap chicken-and-egg: the role can't create itself from inside the workflow
# on the very first run, so .github/workflows/bootstrap.yml applies just this role
# (using a temporary Actions secret), then prints its ARN for a one-time paste into
# the AWS_ROLE_ARN Actions variable. ADR-013.

# The GitHub OIDC provider is an account-wide singleton (one per issuer URL) shared
# across projects (including the sibling repo), so we REFERENCE the existing one
# rather than own it — a `terraform destroy` of this stack must never remove a
# provider other repos depend on, and AWS allows only one provider per issuer URL.
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

variable "github_repo" {
  description = "owner/repo allowed to assume the deploy role, e.g. thayagapriyan/agent-lab."
  type        = string
  default     = "thayagapriyan/agent-lab"
}

data "aws_iam_policy_document" "github_deploy_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"
    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    # Scope to this repo only — any branch/PR/tag.
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:*"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name               = "agent-memory-lab-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_deploy_trust.json
  tags = {
    Project = "agent-memory-lab"
    Purpose = "github-actions-deploy"
  }
}

# The deploy job runs the full `terraform apply`, so the role manages every resource
# in this stack: Bedrock, AgentCore Memory/Runtime, CloudWatch logs, the tfstate
# backend, and IAM (the agent role + this role). PowerUser covers the non-IAM
# services; IAM is granted separately, scoped to the project's own role names.
resource "aws_iam_role_policy_attachment" "github_deploy_poweruser" {
  role       = aws_iam_role.github_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}

data "aws_iam_policy_document" "github_deploy_iam" {
  # Manage the roles/policies this stack owns. Scoped by name prefix so the deploy
  # role can't touch unrelated IAM in the account.
  statement {
    sid    = "ManageProjectRoles"
    effect = "Allow"
    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:GetRole",
      "iam:UpdateRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:PassRole",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:PutRolePolicy",
      "iam:GetRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/agent-memory-lab-*",
    ]
  }

  # The deploy role only READS the GitHub OIDC provider (via the data source on every
  # plan/apply). Resolving by URL needs ListOpenIDConnectProviders (no resource-level
  # scoping, hence "*") to find the ARN, then GetOpenIDConnectProvider (scoped).
  statement {
    sid       = "ListOidcProviders"
    effect    = "Allow"
    actions   = ["iam:ListOpenIDConnectProviders"]
    resources = ["*"]
  }
  statement {
    sid       = "ReadGithubOidcProvider"
    effect    = "Allow"
    actions   = ["iam:GetOpenIDConnectProvider"]
    resources = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"]
  }
}

resource "aws_iam_role_policy" "github_deploy_iam" {
  name   = "manage-project-iam"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.github_deploy_iam.json
}

# Terraform's S3 backend: the deploy job runs `terraform init`, so the role must
# read/write this project's state object + lock file (see infra/backend.tf).
data "aws_iam_policy_document" "github_deploy_tfstate" {
  statement {
    sid       = "TfStateObject"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::agent-memory-lab-tfstate-${data.aws_caller_identity.current.account_id}-${var.aws_region}/agent-memory-lab/*"]
  }
  statement {
    sid       = "TfStateBucket"
    effect    = "Allow"
    actions   = ["s3:ListBucket", "s3:GetBucketVersioning"]
    resources = ["arn:aws:s3:::agent-memory-lab-tfstate-${data.aws_caller_identity.current.account_id}-${var.aws_region}"]
  }
}

resource "aws_iam_role_policy" "github_deploy_tfstate" {
  name   = "tfstate-backend-access"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.github_deploy_tfstate.json
}

output "github_deploy_role_arn" {
  description = "Set this as the GitHub Actions variable AWS_ROLE_ARN."
  value       = aws_iam_role.github_deploy.arn
}
