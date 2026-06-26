"""Agent-SDK catalog — seed family B (DESIGN §8.4; spec 2026-06-26).

Finite, enumerable signatures for frameworks that dispatch a whole sub-agent. Data, not
heuristics: tools can be any function and so are never seeded, but agent SDKs are a closed
set. Contributors add entries here (or via the resolution protocol's contribution step).
The sub-agent itself is a black box by ownership — we recognize the *dispatch*, never its
internals.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentSdk:
    id: str
    framework: str
    calls: tuple[str, ...] = ()  # dotted-suffix call signatures, e.g. "Runner.run", ".invoke"
    constructs: tuple[str, ...] = ()  # constructed symbols that signal an agent, e.g. "Agent"
    carriers: tuple[str, ...] = ()  # outbound carriers paired with a construct, e.g. ".post"
    input_arg: str | None = None
    output_fields: tuple[str, ...] = field(default_factory=tuple)


AGENT_SDKS: tuple[AgentSdk, ...] = (
    AgentSdk("langgraph", "langgraph", calls=(".invoke", ".ainvoke", ".stream"),
             input_arg="input", output_fields=("messages",)),
    AgentSdk("openai-agents", "openai-agents", calls=("Runner.run", "Runner.run_sync"),
             output_fields=("final_output",)),
    AgentSdk("crewai", "crewai", calls=(".kickoff", ".kickoff_async"),
             output_fields=("raw", "tasks_output")),
    AgentSdk("llama-index", "llama-index", calls=(".achat", ".run"),
             output_fields=("response",)),
    AgentSdk("autogen", "autogen", calls=(".initiate_chat", ".run"),
             output_fields=("summary", "chat_history")),
    # OpenHands: an Agent config is constructed and handed to an outbound HTTP carrier.
    AgentSdk("openhands-sdk", "openhands-sdk",
             constructs=("Agent", "StartConversationRequest"),
             carriers=(".post",), output_fields=("events", "final_message")),
)


def match_call_site(dotted: str) -> AgentSdk | None:
    """Return the catalog entry whose `calls` signature matches this call's dotted name.

    A signature starting with "." matches on the trailing attribute (`graph.invoke` →
    ".invoke"); otherwise it must be a dotted suffix (`Runner.run`)."""
    for sdk in AGENT_SDKS:
        for sig in sdk.calls:
            if sig.startswith("."):
                if dotted.endswith(sig) and dotted != sig.lstrip("."):
                    return sdk
            elif dotted == sig or dotted.endswith("." + sig):
                return sdk
    return None


def format_entry(
    id: str,
    framework: str,
    *,
    calls: tuple[str, ...] = (),
    constructs: tuple[str, ...] = (),
    carriers: tuple[str, ...] = (),
    input_arg: str | None = None,
    output_fields: tuple[str, ...] = (),
) -> str:
    """Render a catalog-entry source block an OSS contributor (or the driving harness) can
    paste into AGENT_SDKS."""
    parts = [f'AgentSdk("{id}", "{framework}"']
    if calls:
        parts.append(f"calls={calls!r}")
    if constructs:
        parts.append(f"constructs={constructs!r}")
    if carriers:
        parts.append(f"carriers={carriers!r}")
    if input_arg:
        parts.append(f"input_arg={input_arg!r}")
    if output_fields:
        parts.append(f"output_fields={output_fields!r}")
    return ", ".join(parts) + "),"
