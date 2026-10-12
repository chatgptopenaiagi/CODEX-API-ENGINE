# Windows troubleshooting

| Message or condition | Action |
|---|---|
| Configuration missing | Select operator-provided broker.json. No automatic enrollment occurs. |
| Invalid configuration / executable changed | Ask the operator to verify the current image/hash and configuration. Never disable checks. |
| Broker unavailable | Ask its operator to verify the selected installation is running. Do not restart unrelated production processes. |
| Access denied | The exact GUI image must be enrolled. Ordinary applications cannot grant themselves administration. |
| Remember failed | Directory may be read-only or selection already exists. CAE does not overwrite unknown files. |
| Audit unavailable | Protected operations fail closed. Ask the operator to inspect storage permissions/capacity. |
| Local model unavailable | Check the explicitly configured server with its operator. No cloud fallback is implied. |
| Cloud denied | Explicit provider, model and cloud grants are required; a preference is not permission. |

Do not disable antivirus, Windows security or identity verification. Do not place
keys in bug reports. Report version, Windows build, fixed error code and a synthetic
reproduction through the repository's issue tracker. Exclude private configuration,
prompts, audit exports and credential values. Security reports should follow SECURITY.md.
