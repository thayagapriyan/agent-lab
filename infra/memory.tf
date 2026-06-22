# AgentCore Memory resource + a semantic long-term strategy (Iteration 2).
#
# The memory resource is created once and referenced by ID from the agent
# (MEMORY_ID). Iteration 1 covered Bedrock access; this adds the managed memory
# store. Attaching it to the agent (the injected config / session manager) is
# Iteration 3.
#
# NAMESPACE SCHEME (must match at retrieval time — a mismatch silently returns
# nothing; see DEVELOPMENT.md gotchas). We scope semantic memories per actor:
#
#     semantic/{actorId}
#
# {actorId} is a placeholder AgentCore fills at runtime from the session's actor.
# Per-actor scope means a user's extracted facts are recalled across their
# sessions — which is what the recall experiments need.

resource "aws_bedrockagentcore_memory" "lab" {
  name        = var.memory_name
  description = "Agent Memory Lab — managed memory for the parameter-sweep experiments."

  # ISO 8601 duration in DAYS (provider takes an integer 7–365). Events older than
  # this expire. 90 days is plenty for a learning lab.
  event_expiry_duration = var.memory_event_expiry_days

  tags = {
    Project = "agent-memory-lab"
  }
}

# Semantic strategy: extracts and stores factual information from conversations.
# Start with one strategy (Iteration 2); more can be added later as separate
# resources to sweep the "strategy" parameter.
resource "aws_bedrockagentcore_memory_strategy" "semantic" {
  name       = "semantic"
  memory_id  = aws_bedrockagentcore_memory.lab.id
  type       = "SEMANTIC"
  namespaces = [var.memory_namespace]
}
