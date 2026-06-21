#!/usr/bin/env bash
# Verify Bedrock access with the AWS CLI — independent of the Python agent.
#
# Confirms (1) your credentials work, (2) the configured model is listed/available
# in the region. Does NOT invoke the model (so it does not cost anything).
#
# Usage:
#   AWS_REGION=us-east-1 BEDROCK_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0 \
#     bash scripts/verify_bedrock.sh
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
MODEL_ID="${BEDROCK_MODEL_ID:-anthropic.claude-3-5-haiku-20241022-v1:0}"

echo "== caller identity =="
aws sts get-caller-identity --output table

echo
echo "== is model '$MODEL_ID' available in $REGION? =="
# bedrock (control plane) lists foundation models; bedrock-runtime invokes them.
if aws bedrock list-foundation-models \
      --region "$REGION" \
      --query "modelSummaries[?modelId=='$MODEL_ID'].modelId" \
      --output text | grep -q "$MODEL_ID"; then
  echo "OK: $MODEL_ID is available in $REGION."
else
  echo "NOT FOUND: $MODEL_ID not listed in $REGION." >&2
  echo "Check the model id and that access is granted in the Bedrock console." >&2
  exit 1
fi
