"""Conversions at the LangChain boundary, preserving all protocol IDs."""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from app.models import Message, ToolCall


def to_langchain(message: Message):
    common = {'content': message.content, 'id': message.id}
    if message.role == 'assistant':
        return AIMessage(**common, tool_calls=[{'id': c.id, 'name': c.name, 'args': c.arguments, 'type': 'tool_call'} for c in message.tool_calls])
    if message.role == 'tool':
        return ToolMessage(**common, tool_call_id=message.tool_call_id, name=message.name)
    return (SystemMessage if message.role == 'system' else HumanMessage)(**common)


def from_langchain(message):
    role = {'human': 'user', 'ai': 'assistant'}.get(message.type, message.type)
    return Message(role=role, content=message.content, id=message.id,
                   tool_calls=[ToolCall(id=c['id'], name=c['name'], arguments=c['args']) for c in getattr(message, 'tool_calls', [])],
                   tool_call_id=getattr(message, 'tool_call_id', None), name=getattr(message, 'name', None))
