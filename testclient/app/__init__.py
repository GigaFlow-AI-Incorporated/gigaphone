"""Test customer application — a small AI agent with a hand-rolled LLM gateway.

This stands in for a real customer codebase during GigaPhone's onboarding e2e. It is
deliberately shaped so that, *before* GigaPhone runs, the agent's tool executions are
lost or detached in the trace; *after* GigaPhone's fixes, every tool span lands nested
under the agent trace with a complete payload. See testclient/README.md.
"""
