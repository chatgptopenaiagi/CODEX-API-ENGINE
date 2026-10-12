# Master roadmap M0–M7

Read [history](MILESTONE_HISTORY_M0_M7.md), [checkpoint](CAE_CHECKPOINT.json) and
[next session](NEXT_SESSION.md) first. No completion dates are assumed.

M0–M3 are complete only within their documented contracts; preserve them.

## M4 — centralized administration and human usability (PARTIAL)

Extend the existing Control Center and authenticated ApplicationRegistry. First
deliver trusted, explicit broker selection and a read-only registry/status view.
Then add confirmed registration, authorization/revocation, validated routing/quota
controls, provider diagnostics and audit inspection. Never auto-enroll an unknown
image or grant cloud access. Configuration changes retain existing restart rules.
Acceptance requires isolated GUI/process tests, exact packaged startup outside the
checkout, full regression/native gates and honest release/download evidence.

Development prerelease publication is conditionally authorized by the M4 mission,
only after artifact, secret, licensing, privacy, GUI and fresh-copy gates pass.
Missing gates block publication; source checkpoints may still be synchronized.

## M5 — Windows installation (PLANNED)

Implement user-scoped installer/uninstaller, existing-install detection, trusted
discovery, guided enrollment, optional startup, safe upgrades and data preservation.
Choose tooling after licensing/upgrade evaluation. Test install/repair/upgrade/
uninstall in a disposable Windows environment. No silent elevation, services, PATH
changes or credential deletion. A portable ZIP does not complete M5.

## M6 — hardening and acceptance (PARTIAL)

Extend short recovery evidence with bounded long soak, memory/handle monitoring,
upgrade rollback, actual Windows 11 acceptance, signing investigation, independent
security/privacy review and provider cancellation verification. No Windows 11 claim
from build 19045; no production readiness from test coverage alone.

## M7 — ecosystem integration (PLANNED proposal)

Verify real interfaces before optional POK/ARX/CGC adapters. Keep applications
independent. Preserve consent, moderation, budgets, trusted instructions and offline
operation. CAE does not implement domain mathematics or application-specific safety
policy. Separate authorization is required to modify other repositories.
