# Container image for AgentCore Runtime (Iteration 6).
#
# AgentCore Runtime runs ARM64 containers that expose the /ping + /invocations
# HTTP contract on port 8080 — exactly what `agent.runtime`'s BedrockAgentCoreApp
# serves. Build for linux/arm64 (the CI does `docker buildx --platform linux/arm64`).
#
# We don't install streamlit/pytest here — those are dev/UI deps, not needed to
# serve. Keep the runtime image to what the agent needs to answer a prompt.

FROM --platform=linux/arm64 python:3.12-slim

WORKDIR /app

# Install only the serving deps (not the full requirements.txt dev/UI set).
RUN pip install --no-cache-dir \
    "strands-agents>=1.44.0" \
    "bedrock-agentcore>=1.15.0" \
    "boto3>=1.34.0"

# Copy the packages the server imports. ui/, harness/, probes/, tests/ aren't
# needed to serve, so they stay out of the image.
COPY agent/ ./agent/
COPY memory/ ./memory/

EXPOSE 8080

CMD ["python", "-m", "agent.runtime"]
