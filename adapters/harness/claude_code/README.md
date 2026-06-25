# Claude Code plugin

The Claude Code plugin **is the repository root** — `.claude-plugin/plugin.json` +
`.claude-plugin/marketplace.json` + `skills/gigaphone/` + `hooks/hooks.json`, all generated
from the single source `src/gigaphone/adapters/harness/manifest.py` by
`scripts/build_plugins.py`. The repo root is the plugin so the cloned engine is reachable
from `${CLAUDE_PLUGIN_ROOT}` (the MCP server + post-edit hook launch it with `uv`).

Install:
```
claude plugin marketplace add GigaFlow-AI-Incorporated/gigaphone
claude plugin install gigaphone@gigaphone
```
