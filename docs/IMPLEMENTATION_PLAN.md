# Implementation Plan — v1

> **Status: v1 shipped (M0–M6 done).** The full pipeline runs end-to-end; see
> `progress.json` for per-milestone status and the e2e-verified path. This document is
> kept as the record of how it was sequenced and what each milestone delivered. Remaining
> work (tree-sitter-backed TS, a TS e2e, Arize/Logfire backends, marketplace packaging) is
> v2 — see §"v2" in `docs/DESIGN.md` and `progress.json.next_task`.

Sequenced depth-first per harness-engineering: build a small block, verify it, then
unlock the next. Each milestone is shippable and testable on its own. The neutral
core lands first so every axis has a stable spine to plug into.

> Process: **plan → execute one task → verify with tests** before declaring a
> milestone done. Update `progress.json` at session end. Keep ADRs and `AGENTS.md`
> current when a rule changes.

## M0 — Scaffold (this commit)

- Repo skeleton, `AGENTS.md`, `DESIGN.md`, ADRs, golden principles, SKILL.md body.
- `pyproject.toml` with Ruff + pytest; `gigaphone` CLI entrypoint stubbed (`--help` works).
- Interface ABCs declared (`LanguagePack`, `BackendAdapter`, `HarnessAdapter`).
- Boundary-config schema + an example `gigaphone.boundaries.yaml`.

## M1 — Neutral core spine

- Plan-record + boundary dataclasses and JSON (de)serialization (§11).
- Classifier skeleton: failure-mode taxonomy types, no detection logic yet (§10).
- CLI subcommands wired (`discover/detect/plan/resolve/fix/verify`) to no-op handlers
  that read/write the documented JSON contracts.
- Config loader + drift-check stub for `gigaphone.boundaries.yaml` (§8).
- **Verify:** golden-file tests on the JSON contracts; `gigaphone plan` round-trips a fixture.

## M2 — Python language pack (depth on one axis)

- tree-sitter-python grammar wired; anchor queries for the §7.1 catalog.
- Shallow same-file def-use (sink ← value ← producing fn).
- `off_context` signatures for Python's concurrency model (contextvars / pools /
  `run_in_executor` / `asyncio.to_thread`; `create_task` copies context — don't flag).
- Codemod emitters (insert/wrap) using byte ranges; idempotent.
- **Verify:** query + classify fixtures covering each failure mode; a *breaking* fixture
  per mode so each fix is demonstrable (golden-principle: no fix without a red fixture).

## M3 — Generic OTel backend adapter (depth on one axis)

- `trace_boundary` / `restore_context` / `map_output` primitives via OpenInference + OTel.
- `init_snippet`, `detect_presence`, `verify` against an OTLP backend (collector in tests).
- **Verify:** end-to-end on a sample agent loop — inject a fault, fix, confirm nested
  complete tool spans via the same read path the eval platform uses (§12).

## M4 — Discovery + resolution protocols

- `discover` (scoped + full-repo): emit files-to-read + descriptor schema; ingest
  confirmed descriptors → `gigaphone.boundaries.yaml` (§8.2–8.3).
- `resolve`: emit `unresolved.json`, ingest `resolution.json`; schema-validate + re-prompt.
- Drift detection: anchors no longer resolve → flag + re-trigger Phase A for the area (§8.5).
- **Verify:** discovery on a fixture repo with a hand-rolled `our_llm.chat` gateway
  produces the expected descriptors; round-trip the resolution protocol.

## M5 — Harness adapters (Claude Code + Codex)

- Shared `SKILL.md` body; per-harness `skill_frontmatter`, manifest, hooks (plain shell
  commands so Codex's command-only hooks work), `present_diff`, `register_mcp`.
- Generate both manifests from one source.
- MCP verifier server wired into both harnesses.
- **Verify:** drive discovery + resolution through each harness against the M4 fixture.

## M6 — Second language + native backends + CI mode

- TypeScript language pack (grammar + queries + def-use + AsyncLocalStorage hop-sigs + emitters).
- Braintrust + LangSmith native backend adapters (contextvars family; reuse fix logic).
- Head-less CI mode off the committed config ("did anyone add an untraced tool?").
- **Verify:** TS fixture parity with Python; native-adapter verify; CI regression run.

## Cross-cutting acceptance

Every tool a fixture exercises must be reported **nested + complete** by a backend
`verify()` before it is counted as covered (ADR-0005). The onboarding report (§12) is
the user-facing acceptance artifact.
