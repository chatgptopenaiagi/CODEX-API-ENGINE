# Implementation references

Official documentation consulted during implementation on 2026-10-11:

- [OpenAI model listing](https://developers.openai.com/api/reference/resources/models/methods/list): authenticated GET `/v1/models`.
- [OpenAI API overview](https://developers.openai.com/api/reference/overview): API authentication and error/reference entry points.
- [OpenAI Responses reference](https://developers.openai.com/api/reference/python/resources/responses/methods/create): request input, output limits, response storage and usage fields.
- [Microsoft CredWriteW](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew): native credential writes.
- [Microsoft CREDENTIALW](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw): credential layout, persistence and blob ownership.
- [Microsoft CredReadW](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credreadw): account-scoped reads and CredFree ownership.

Model access, quota and billing are account-specific. The connection probe only
establishes the observed model-list request result at the time of validation.
