# CAE milestone history M0–M7

M0 is a retrospective label, not a historical release name. Milestones describe
verified scope, not production certification. Git history and the linked dated
reports remain authoritative; local artifacts are not public releases.

| Milestone | Status | Evidence and scope |
|---|---|---|
| M0 foundation | COMPLETED within original contract | Published v0.2.0: Windows vault, OpenAI API, in-process SDK, console, tests and packaging. Later v0.3.1 added independent named pipes and two clients; d969373 added multi-language clients; 327bd2f added registry and limits. [Historical evidence](COMPLETED_MILESTONES.md) |
| M1 audit | COMPLETED within tested contract | 02153a7 correlation, 9768e4a retention, ac55a2f checkpoint. Managed JSONL requires explicit opt-in; production legacy logs were not migrated. [Report](../validation/AUDIT-M1-RETENTION-ROTATION.md) |
| M2 routing | COMPLETED within tested contract | ee1947e implementation, bf238e2 checkpoint, dev4. Versioned capabilities, exact authorization, locality, quotas and conservative fallback. Provider combinations primarily mock-tested. [Report](../validation/ROUTING-M2.md) |
| M3 local inference | COMPLETED within packaged/isolated-recovery contract | 9b31d14 exact model IDs, bf6107f HTTP integrity, d222927 acceptance, 25e3fe8 checkpoint, dev5. Real packaged Qwen inference; disposable endpoint recovery. Real Qwen restart NOT_RUN. [Report](../validation/LOCAL-INFERENCE-M3-PACKAGED.md) |
| M4 administration/usability | PARTIALLY COMPLETED | Existing trusted-host Control Center and registry CLI; current mission adds human startup and release preparation. [Current report](../validation/HUMAN-FIRST-M4.md) |
| M5 installation | PLANNED / NOT STARTED | No validated installer, uninstaller or upgrade workflow. Portable executables are not installer acceptance. |
| M6 stable acceptance | PARTIALLY COMPLETED | Short failure/recovery tests exist; long soak, Windows 11, signing, independent security review and upgrades remain NOT VERIFIED. |
| M7 ecosystem | PLANNED | Proposed future milestone; no operational POK/ARX/CGC adapter claim. [POK gaps](../integrations/POK_COMPATIBILITY.md) |

Only v0.2.0 and v0.3.1 were public releases at M4 entry. Development versions
0.5.0.dev1–dev5 have separate local artifacts. Never rewrite their reports or tags.
