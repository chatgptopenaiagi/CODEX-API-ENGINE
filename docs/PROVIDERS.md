# Provider adapters

| Adapter | Models | Single-text chat | Embeddings | Authentication |
|---|---|---|---|---|
| OpenAI | Yes | Responses API | Yes | Bearer key |
| Azure OpenAI | Yes | v1 chat completions | Yes | `api-key` |
| Anthropic | Yes | Messages API | Explicitly unsupported | `x-api-key` |
| Gemini | Yes | generateContent | embedContent | `x-goog-api-key` |
| Ollama | Local tags | Local chat | Local embed | None |
| vLLM | Compatible API | Compatible API | Server/model dependent | Optional bearer |
| LM Studio | Compatible API | Compatible API | Server/model dependent | Optional bearer |

Cloud credentials are acquired internally by the broker. Google credentials are
sent in a header, never a query string. Cloud hosts are fixed; Azure permits an
explicit `https://<resource>.openai.azure.com` origin only. Local adapters accept
literal `127.0.0.1` or `[::1]` with an explicit port, avoiding DNS rebinding and
accidental credential forwarding to a LAN/remote endpoint. No redirects or environment
proxies are used. TLS validation remains enabled for HTTPS. Administrators must trust
the local service bound to the selected loopback port.

Responses are normalized: chat returns `text` and `usage`; embeddings returns
`vectors` and `usage`; models are string IDs. `usage.reported` distinguishes provider
reported tokens from unavailable token counts. Runtime usage counters are not billing
or account-wide usage. Listing is one page; adapter results flag pagination with
`truncated`, while the convenience `list_models()` returns that first page's IDs.
Some endpoints/operations depend on deployment/model configuration and can fail even
when the adapter supports the wire protocol.

Custom/future providers implement the typed `ProviderAdapter` protocol and are
explicitly injected by trusted host code. `ProviderConfig(kind="custom")` has no
arbitrary configured endpoint. JSON/TOML cannot load arbitrary Python adapters.
Applications receive `ProviderSession`, not a transport, adapter or secret.

All seven adapters have mocked contract tests. No new cloud credentials were created
and no live generation or embedding requests were made during this implementation.

Official references consulted:

- [OpenAI Responses](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
- [Azure OpenAI v1](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle?tabs=key)
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create) and [Models](https://platform.claude.com/docs/en/api/models/list)
- [Gemini API](https://ai.google.dev/api)
- [Ollama chat](https://docs.ollama.com/api/chat) and [embeddings](https://docs.ollama.com/api/embed)
- [vLLM compatible server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/)
- [LM Studio compatibility](https://lmstudio.ai/docs/developer/openai-compat)

## llama.cpp compatibility validation

The existing vLLM OpenAI-compatible wire adapter was tested with llama.cpp/Qwen.
It is compatibility reuse, not a claim that the server runs vLLM. Exact allowlisted
model IDs may contain backslashes; they are opaque identifiers, never file access.
Only message.content becomes assistant text; reasoning_content is ignored.
See [real M3 evidence](validation/LOCAL-INFERENCE-M3.md).
