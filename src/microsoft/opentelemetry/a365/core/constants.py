# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Constants for the Agent365 OpenTelemetry implementation.

Span operation names and OpenTelemetry semantic-convention attribute keys
shared across the Agent365 core scopes and exporters.
"""

# --- Span operation names ---
INVOKE_AGENT_OPERATION_NAME = "invoke_agent"
EXECUTE_TOOL_OPERATION_NAME = "execute_tool"
OUTPUT_MESSAGES_OPERATION_NAME = "output_messages"
CHAT_OPERATION_NAME = "chat"
APPLY_GUARDRAIL_OPERATION_NAME = "apply_guardrail"

# --- OpenTelemetry semantic conventions ---
ERROR_TYPE_KEY = "error.type"
ERROR_MESSAGE_KEY = "error.message"
AZ_NAMESPACE_KEY = "az.namespace"
AZURE_RP_NAMESPACE_VALUE = "Microsoft.CognitiveServices"
SOURCE_NAME = "Agent365Sdk"

# --- Feature switches ---
ENABLE_OPENTELEMETRY_SWITCH = "Azure.Experimental.EnableActivitySource"
TRACE_CONTENTS_SWITCH = "Azure.Experimental.TraceGenAIMessageContent"
TRACE_CONTENTS_ENVIRONMENT_VARIABLE = "AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"
ENABLE_OBSERVABILITY = "ENABLE_OBSERVABILITY"
ENABLE_A365_OBSERVABILITY_EXPORTER = "ENABLE_A365_OBSERVABILITY_EXPORTER"
ENABLE_A365_OBSERVABILITY = "ENABLE_A365_OBSERVABILITY"

# --- GenAI semantic conventions ---
GEN_AI_CLIENT_OPERATION_DURATION_METRIC_NAME = "gen_ai.client.operation.duration"
GEN_AI_CLIENT_TOKEN_USAGE_METRIC_NAME = "gen_ai.client.token.usage"
GEN_AI_OPERATION_NAME_KEY = "gen_ai.operation.name"
GEN_AI_DATA_SOURCE_ID_KEY = "gen_ai.data_source.id"
GEN_AI_OUTPUT_TYPE_KEY = "gen_ai.output.type"
GEN_AI_REQUEST_CHOICE_COUNT_KEY = "gen_ai.request.choice.count"
GEN_AI_REQUEST_FREQUENCY_PENALTY_KEY = "gen_ai.request.frequency_penalty"
GEN_AI_REQUEST_MAX_TOKENS_KEY = "gen_ai.request.max_tokens"
GEN_AI_REQUEST_MODEL_KEY = "gen_ai.request.model"
GEN_AI_REQUEST_PRESENCE_PENALTY_KEY = "gen_ai.request.presence_penalty"
GEN_AI_REQUEST_SEED_KEY = "gen_ai.request.seed"
GEN_AI_REQUEST_STOP_SEQUENCES_KEY = "gen_ai.request.stop_sequences"
GEN_AI_REQUEST_TEMPERATURE_KEY = "gen_ai.request.temperature"
GEN_AI_REQUEST_TOP_P_KEY = "gen_ai.request.top_p"
GEN_AI_RESPONSE_FINISH_REASONS_KEY = "gen_ai.response.finish_reasons"
GEN_AI_RESPONSE_MODEL_KEY = "gen_ai.response.model"
GEN_AI_RESPONSE_ID_KEY = "gen_ai.response.id"
GEN_AI_AGENT_ID_KEY = "gen_ai.agent.id"
GEN_AI_AGENT_NAME_KEY = "gen_ai.agent.name"
GEN_AI_AGENT_DESCRIPTION_KEY = "gen_ai.agent.description"
GEN_AI_AGENT_VERSION_KEY = "gen_ai.agent.version"
GEN_AI_AGENT_PLATFORM_ID_KEY = "microsoft.a365.agent.platform.id"
GEN_AI_AGENT_THOUGHT_PROCESS_KEY = "microsoft.a365.agent.thought.process"
GEN_AI_CONVERSATION_ID_KEY = "gen_ai.conversation.id"
GEN_AI_CONVERSATION_ITEM_LINK_KEY = "microsoft.conversation.item.link"
GEN_AI_TOKEN_TYPE_KEY = "gen_ai.token.type"
GEN_AI_USAGE_CACHE_WRITE_INPUT_TOKENS_KEY = "gen_ai.usage.cache_write.input_tokens"
GEN_AI_USAGE_CACHE_READ_INPUT_TOKENS_KEY = "gen_ai.usage.cache_read.input_tokens"
GEN_AI_USAGE_INPUT_TOKENS_KEY = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS_KEY = "gen_ai.usage.output_tokens"
GEN_AI_CHOICE = "gen_ai.choice"
GEN_AI_PROVIDER_NAME_KEY = "gen_ai.provider.name"
GEN_AI_SYSTEM_INSTRUCTIONS_KEY = "gen_ai.system_instructions"
GEN_AI_INPUT_MESSAGES_KEY = "gen_ai.input.messages"
GEN_AI_OUTPUT_MESSAGES_KEY = "gen_ai.output.messages"

# --- Tool execution ---
GEN_AI_TOOL_CALL_ID_KEY = "gen_ai.tool.call.id"
GEN_AI_TOOL_NAME_KEY = "gen_ai.tool.name"
GEN_AI_TOOL_DESCRIPTION_KEY = "gen_ai.tool.description"
GEN_AI_TOOL_ARGS_KEY = "gen_ai.tool.call.arguments"
GEN_AI_TOOL_CALL_RESULT_KEY = "gen_ai.tool.call.result"
GEN_AI_TOOL_TYPE_KEY = "gen_ai.tool.type"

# --- Human caller ---
USER_ID_KEY = "user.id"
USER_NAME_KEY = "user.name"
USER_EMAIL_KEY = "user.email"
GEN_AI_CALLER_CLIENT_IP_KEY = "client.address"

# --- Agent-to-Agent caller ---
GEN_AI_CALLER_AGENT_USER_ID_KEY = "microsoft.a365.caller.agent.user.id"
GEN_AI_CALLER_AGENT_EMAIL_KEY = "microsoft.a365.caller.agent.user.email"
GEN_AI_CALLER_AGENT_NAME_KEY = "microsoft.a365.caller.agent.name"
GEN_AI_CALLER_AGENT_ID_KEY = "microsoft.a365.caller.agent.id"
GEN_AI_CALLER_AGENT_APPLICATION_ID_KEY = "microsoft.a365.caller.agent.blueprint.id"
GEN_AI_CALLER_AGENT_PLATFORM_ID_KEY = "microsoft.a365.caller.agent.platform.id"
GEN_AI_CALLER_AGENT_VERSION_KEY = "microsoft.a365.caller.agent.version"

# --- Agent-specific dimensions ---
AGENT_ID_KEY = "gen_ai.agent.id"
GEN_AI_TASK_ID_KEY = "gen_ai.task.id"
GEN_AI_ICON_URI_KEY = "gen_ai.agent365.icon_uri"
GEN_AI_EXECUTION_PAYLOAD_KEY = "gen_ai.execution.payload"
TENANT_ID_KEY = "microsoft.tenant.id"
GEN_AI_AGENT_AUID_KEY = "microsoft.agent.user.id"
GEN_AI_AGENT_EMAIL_KEY = "microsoft.agent.user.email"
GEN_AI_AGENT_BLUEPRINT_ID_KEY = "microsoft.a365.agent.blueprint.id"
SESSION_ID_KEY = "microsoft.session.id"
SESSION_DESCRIPTION_KEY = "microsoft.session.description"

# --- Error type constants ---
ERROR_TYPE_CANCELLED = "TaskCanceledException"

# --- OTel standard keys ---
SERVER_ADDRESS_KEY = "server.address"
SERVER_PORT_KEY = "server.port"
SERVICE_NAME_KEY = "service.name"

# --- Custom span keys ---
CUSTOM_PARENT_SPAN_ID_KEY = "custom.parent.span.id"
CUSTOM_SPAN_NAME_KEY = "custom.span.name"

# --- Channel ---
CHANNEL_NAME_KEY = "microsoft.channel.name"
CHANNEL_LINK_KEY = "microsoft.channel.link"

# --- Guardrail / Security ---
GEN_AI_GUARDIAN_ID_KEY = "microsoft.guardian.id"
GEN_AI_GUARDIAN_NAME_KEY = "microsoft.guardian.name"
GEN_AI_GUARDIAN_PROVIDER_NAME_KEY = "microsoft.guardian.provider.name"
GEN_AI_GUARDIAN_VERSION_KEY = "microsoft.guardian.version"
GEN_AI_SECURITY_DECISION_TYPE_KEY = "microsoft.security.decision.type"
GEN_AI_SECURITY_DECISION_REASON_KEY = "microsoft.security.decision.reason"
GEN_AI_SECURITY_DECISION_CODE_KEY = "microsoft.security.decision.code"
GEN_AI_SECURITY_TARGET_TYPE_KEY = "microsoft.security.target.type"
GEN_AI_SECURITY_TARGET_ID_KEY = "microsoft.security.target.id"
GEN_AI_SECURITY_POLICY_ID_KEY = "microsoft.security.policy.id"
GEN_AI_SECURITY_POLICY_NAME_KEY = "microsoft.security.policy.name"
GEN_AI_SECURITY_POLICY_VERSION_KEY = "microsoft.security.policy.version"
GEN_AI_SECURITY_CONTENT_INPUT_HASH_KEY = "microsoft.security.content.input.hash"
GEN_AI_SECURITY_CONTENT_MODIFIED_KEY = "microsoft.security.content.modified"
GEN_AI_SECURITY_EXTERNAL_EVENT_ID_KEY = "microsoft.security.external_event_id"
GEN_AI_SECURITY_CONTENT_INPUT_VALUE_KEY = "microsoft.security.content.input.value"
GEN_AI_SECURITY_CONTENT_OUTPUT_VALUE_KEY = "microsoft.security.content.output.value"
GEN_AI_SECURITY_FINDING_EVENT_NAME = "microsoft.security.finding"
GEN_AI_SECURITY_RISK_CATEGORY_KEY = "microsoft.security.risk.category"
GEN_AI_SECURITY_RISK_SEVERITY_KEY = "microsoft.security.risk.severity"
GEN_AI_SECURITY_RISK_SCORE_KEY = "microsoft.security.risk.score"
GEN_AI_SECURITY_RISK_METADATA_KEY = "microsoft.security.risk.metadata"
GEN_AI_SECURITY_POLICY_DECISION_TYPE_KEY = "microsoft.security.policy.decision.type"

# --- Telemetry SDK attributes ---
TELEMETRY_SDK_NAME_KEY = "telemetry.sdk.name"
TELEMETRY_SDK_LANGUAGE_KEY = "telemetry.sdk.language"
TELEMETRY_SDK_VERSION_KEY = "telemetry.sdk.version"
TELEMETRY_SDK_NAME_VALUE = "microsoft-opentelemetry"
TELEMETRY_SDK_LANGUAGE_VALUE = "python"
