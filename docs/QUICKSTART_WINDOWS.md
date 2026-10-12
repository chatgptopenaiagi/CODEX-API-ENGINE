# Windows Control Center quickstart (M4 development)

1. Launch CAE-Control-Center.exe. No flags or Python installation are needed for the
   packaged GUI. The Broker page explains missing configuration; it does not exit.
2. Choose an existing broker.json supplied by your trusted operator. Review the
   executable path and SHA-256 before confirming. This selection grants no access.
3. Click **Check verified broker status**. CAE verifies the named-pipe peer against
   the configured image and hash. It never scans ports or starts an unknown broker.
4. If the exact Control Center executable is already enrolled as administrator,
   use Applications to list grants and limits, register an exact EXE without provider
   permissions, or revoke a non-administrator. Both mutations require confirmation.
5. **Remember selection for next launch** creates a non-secret
   `cae-control-selection.json` beside the portable EXE. It never overwrites an
   existing file. Keep this directory private. Relaunch verifies the saved identity
   offline; status is fetched only when requested. Same-account hostile tampering
   is not prevented by this descriptor.

No broker is provisioned or administrator silently enrolled during first launch.
An operator must use the existing [enrollment procedure](BROKER_PROTOCOL.md) and
[administrative CLI](APPLICATION_REGISTRY.md). Fresh-install setup and graphical
authorization/provider/routing editing remain unfinished; this is not yet a fully
beginner-ready installation flow. A rebuilt EXE requires explicit re-enrollment.

Overview, Providers, Credentials, Audit and Policies are the retained **separate
in-process** administration interface. They do not control the broker selected on
the Broker page. Do not mistake their status for that broker's status. No connection
or credential action happens merely from launching the GUI.

Registration grants no provider access. Policy updates require broker restart by
its operator. Revocation reports next-connection or restart timing; it does not
cancel already accepted work. Request quotas are not monetary billing caps.
Closing the GUI leaves independent brokers running.
