# Broker design

The trusted host instantiates `Broker(store, grants, connector)` and injects it into
application SDK instances. A frozen `Grant` authorizes exactly one application/profile
pair for the `models` and/or `responses` operation. No match means deny. A denied call
does not read credentials or contact the network.

The broker acquires the key only for a request, invokes the fixed-origin connector,
and returns sanitized results. Audit records contain a UTC timestamp and one of
`success`, `denied`, `credential_failed`, `request_failed`. The ring holds 100 events;
`audit()` returns copies and has no secret fields or request content.

This release deliberately opens no TCP port or named pipe. It does not claim process
identity validation or protection against other programs under the same Windows user.
That requires a separate service identity plus OS-authenticated IPC. See Phase 3 in
the roadmap. A localhost HTTP listener with a caller-supplied app name would not
solve that security problem and is not implemented.

Treat app profiles as namespace/policy separation within a Windows-account boundary.
The application SDK has no raw-key operation; trusted backend implementers necessarily
have access to secrets. There is no export endpoint and no bearer broker token on disk.
