# Remote state in S3, with S3-native locking (use_lockfile, Terraform >= 1.10 —
# no DynamoDB table required). The bucket is created once by infra/bootstrap/.
#
# If you run this in a fresh clone: first `cd bootstrap && terraform apply`, then
# come back here and `terraform init` (Terraform will configure this backend).
#
# Bucket name is deterministic: agent-memory-lab-tfstate-<account-id>-<region>.
terraform {
  backend "s3" {
    bucket       = "agent-memory-lab-tfstate-224193574799-us-east-1"
    key          = "agent-memory-lab/main.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
