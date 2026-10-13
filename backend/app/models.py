"""Poseidon domain contracts. No framework message or graph types belong here."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator, field_validator

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
Channel = Literal['web', 'telegram', 'slack', 'whatsapp', 'cli']
RESERVED_ARGUMENTS = {'owner_id', 'user_id', 'approved', '_operator_approved', 'is_tainted', 'taint_sources', 'role', 'roles', 'permission_override', 'actor', 'conversation_key', 'run_id', 'agent_id'}


class DomainModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ActorContext(DomainModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    owner_id: Identifier = 'local_owner'
    is_operator: bool = False


class ConversationKey(DomainModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    owner_id: Identifier
    channel: Channel
    channel_account_id: Identifier
    thread_id: Identifier


class InboundEvent(DomainModel):
    actor: ActorContext
    conversation_key: ConversationKey
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_tainted: bool = False
    taint_sources: list[str] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def legacy_internal_event(cls, value):
        # Compatibility for internal callers only; HTTP adapters derive identity.
        data = dict(value)
        owner = data.pop('user_id', 'local_owner')
        channel = data.pop('channel', 'web')
        thread = data.pop('channel_thread_id', 'default')
        data.setdefault('actor', ActorContext(owner_id=owner))
        data.setdefault('conversation_key', ConversationKey(owner_id=owner, channel=channel, channel_account_id='local_browser' if channel == 'web' else channel, thread_id=thread))
        return data

    @model_validator(mode='after')
    def matching_owner(self):
        if self.actor.owner_id != self.conversation_key.owner_id:
            raise ValueError('Actor and conversation owners must match')
        return self

    @property
    def user_id(self):
        return self.actor.owner_id

    @property
    def channel(self):
        return self.conversation_key.channel

    @property
    def channel_thread_id(self):
        return self.conversation_key.thread_id


class ToolCall(DomainModel):
    id: Identifier
    name: Identifier
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator('arguments')
    @classmethod
    def business_arguments_only(cls, value):
        if RESERVED_ARGUMENTS.intersection(value):
            raise ValueError('Trusted execution fields are not tool arguments')
        return value


class ToolResult(DomainModel):
    tool_call_id: Identifier
    tool_name: Identifier
    result: Any
    status: Literal['completed', 'failed', 'denied', 'limited'] = 'completed'


class Message(DomainModel):
    role: Literal['system', 'user', 'assistant', 'tool']
    content: str = ''
    id: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: Identifier | None = None
    name: str | None = None

    @model_validator(mode='after')
    def validate_tool_message(self):
        if self.role == 'tool' and not self.tool_call_id:
            raise ValueError('Tool messages require a tool_call_id')
        if self.tool_calls and self.role != 'assistant':
            raise ValueError('Only assistant messages can request tools')
        return self


class ToolExecutionContext(DomainModel):
    actor: ActorContext
    conversation_key: ConversationKey
    run_id: Identifier
    agent_id: Identifier
    is_tainted: bool = False
    taint_sources: list[str] = Field(default_factory=list)


class PolicyDecision(DomainModel):
    decision: Literal['allow', 'guard', 'require_approval', 'deny']
    reasons: list[str] = Field(default_factory=list)
    policy_version: str = '1'


class ApprovalRequest(DomainModel):
    approval_id: Identifier
    run_id: Identifier
    owner_id: Identifier
    conversation_key: ConversationKey
    tool_call_id: Identifier
    tool_name: Identifier
    arguments: dict[str, Any] = Field(default_factory=dict)
    arguments_hash: Identifier
    policy_version: str = '1'
    status: Literal['pending', 'approved', 'denied', 'expired', 'consumed'] = 'pending'
    created_at: datetime
    expires_at: datetime


class ApprovalDecision(DomainModel):
    approval_id: Identifier
    decision: Literal['approved', 'denied']


class AgentDefinition(DomainModel):
    id: Identifier
    display_name: Identifier
    persona: str = ''
    allowed_tools: list[str] = Field(default_factory=list)
    routing_signals: list[str] = Field(default_factory=list)
    model_preset: str = 'env'


class MemoryHit(DomainModel):
    id: Identifier
    tier: Literal['working', 'episodic', 'semantic', 'procedural']
    text: str
    owner_id: Identifier
    conversation_key: ConversationKey | None = None
    source_run_id: str | None = None
    lexical_rank: int | None = None
    vector_rank: int | None = None
    fused_score: float | None = None
    is_tainted: bool = False
    embedding_version: str | None = None
    lifecycle_status: str = 'active'


class RunResult(DomainModel):
    reply: str
    run_id: Identifier
    active_agent: Identifier
    thread_id: Identifier
    conversation_key: ConversationKey
    approval_request: dict[str, Any] | None = None
    memory_context: dict[str, Any] = Field(default_factory=dict)
    trajectory: list[dict[str, Any]] = Field(default_factory=list)
