# Migration from v0.2.0

The platform name becomes CODEX ACCESS ENGINE. Repository `CODEX-API-ENGINE`, package
`codex-api-engine`, import `cae` and existing OpenAI credentials remain compatible.
The Windows target for OpenAI is still `CAE/openai/<profile>`; no migration of existing
keys is needed or performed. Other provider kinds use `CAE/<kind>/<profile>`.

Default `CAE()` uses the capability runtime in v0.3.0. Existing `configure`,
`get_status`, `test_connection` and `list_models` calls remain. Status schema 2 adds
provider, policy and latency metadata. Offline snapshots explicitly distinguish
unknown health from an observed result. `connect()` probes; `health()` is offline.

Trusted hosts that explicitly inject the old `Broker` retain the old API response
shape and behavior. New provider-session methods require an `AccessRuntime`; they
never silently bypass an injected legacy policy. For the new runtime,
`create_response` returns normalized chat output; use `provider.chat` in new code.
No unrestricted response-generation capability is added to the default console.

Credential administration adds a provider namespace and audit injection. Existing
OpenAI validation/storage stays intact. Local removal/rotation does not revoke or
issue a key at the provider. Provider-side revocation remains a human account action.

Builds now write to `dist/<version>/` and create `CAE-Control-Center.exe`. Existing
v0.2.0 assets at the root of `dist/` are preserved. Published v0.2.0 tags and assets
are not replaced. v0.3.0 is not published automatically by this development task.

Use `scripts/release.ps1` for a tested local build with checksums. The manual release
workflow can publish a pre-existing version tag after validation; it has no scheduled
trigger, no stored provider credentials and no automatic main-branch publication.
