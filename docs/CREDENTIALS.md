# Credential administration

Use `cae add` for a new profile, `cae replace` for an existing profile, and
`cae --profile application-a add` for a separate application namespace. Keys enter via
`getpass`; if the terminal cannot hide input, CAE refuses the fallback.

`CredentialManager.add`, `.replace`, `.rotate`, `.remove`, `.exists`, and `.import_file`
form the administration surface. This interface is separate from `CAE`. Imports
accept a small UTF-8/BOM file containing only the key and surrounding whitespace.
They reject oversized files and symlinks, and never delete or rewrite the source.

The existing `apy_key.txt` is retained unchanged at the user's instruction. Do not
move, rename, overwrite, modify or delete it, and do not ask again about deletion.
Git ignores it and package checks reject its inclusion.

Storage target: `CAE/openai/<profile>`. Profiles are 1–64 lowercase ASCII letters,
digits, underscores or hyphens, beginning with a letter or digit. Storage uses the
current Windows user's Credential Manager with local-machine persistence.

Successful import means a write and exact readback matched; it does not alone prove
the credential is accepted by OpenAI. `test_connection()` performs that separate
validation. Missing credentials and backend errors are distinct conditions internally.

Local replacement does not revoke the previous key in OpenAI. For rotation, create a
new restricted key through your account's approved process, replace locally, validate,
then revoke the old key in OpenAI. No raw credential export is supported.
