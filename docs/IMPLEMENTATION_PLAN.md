# v0.2.0 implementation and validation plan

1. Exclude the retained input key before initializing version control.
2. Implement Win32 protected storage, readback verification and separate administration.
3. Import directly from the source file without printing or duplicating plaintext.
4. Validate with one authenticated model-list GET, preserving the source file.
5. Build default-deny broker grants, SDK, explicit generation and health diagnostics.
6. Add CLI and masked threaded GUI as consumers of the engine.
7. Test lifecycle, negative authorization, exception sanitation, retry bounds, protocol
   validation, monitoring, native vault roundtrip, GUI behavior and package exclusions.
8. Type-check, lint, build source/wheel/executable and verify artifact contents.
9. Record validation evidence, limitations and remaining roadmap work.

The user explicitly requires the original key file to remain unchanged. No deletion
is part of implementation or release tasks. No credentials enter tests or artifacts.

Longer-term tasks are tracked in ROADMAP.md. Implementing enterprise identity or
multi-provider adapters requires separate design and validation milestones.
