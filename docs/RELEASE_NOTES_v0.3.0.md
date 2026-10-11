# CODEX ACCESS ENGINE v0.3.0

Development candidate; not yet published.

CAE evolves from the OpenAI integration foundation into a provider capability platform:
seven provider adapters, deny-overrides TOML policy, model allowlists, persistent
atomic daily quotas, structured metadata audit, normalized health/usage, extended CLI,
Control Center and typed ARX/CGC integration contracts.

Application SDK calls never accept or return raw credentials. The existing OpenAI
Windows credential target is unchanged. The broker remains in-process for trusted
hosts; it does not isolate hostile same-user programs. Anthropic embeddings are
explicitly unsupported. Chat is single-text and non-streaming. New cloud provider
contracts are mock-tested, not live-certified. The Windows executable is unsigned.

See docs/MIGRATION_0.3.md for compatibility and status-schema changes. Existing v0.2.0
release assets are preserved. Build outputs are under dist/0.3.0/.
