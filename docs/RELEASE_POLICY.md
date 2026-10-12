# Release channels and objective gates

Stable releases, development prereleases and source checkpoints are distinct.
M4 authorizes a development prerelease only after all gates pass. It does not
authorize a stable release, main merge, tag replacement or PyPI upload.

Required gates: immutable committed runtime source; verified repository/account;
new version/output directory; full regression/security/native/GUI tests; packaged
fresh-copy startup outside the source checkout; wheel/sdist/source completeness;
artifact-source matching and hashes; redacted source/history/archive/binary secret
scans; redistribution license notices; privacy review; accurate release notes;
historical preservation. Missing evidence blocks publication.

Prefer one portable Windows ZIP, wheel and complete source archive, accompanied by
SHA256SUMS.txt/json and RELEASE_MANIFEST.json. Include README-FIRST and upstream
notices. Publish only real validated assets; no placeholder installer. Installer
acceptance belongs to M5. Unsigned and Windows 11 NOT_RUN must be conspicuous.

Before publication independently copy the exact candidate and execute it. After
publication download assets from GitHub, compare hashes and repeat smoke tests.
Record source/build commit, environment, artifact sizes/hashes, tested OS,
dependencies, signature status, limitations and validation links. Builds are not
claimed bit-for-bit reproducible without evidence. Never replace published bytes.

If a gate fails: RELEASE_NOT_PUBLISHED, preserve local candidates, document the
blocker and request operator review. Do not bypass gates to satisfy downloadability.
