# Baseline before universal clients

Verified 2026-10-11, before implementation changes. Source: main
`8b8bf3d4ece60a6448921381cb1755abd9b46e1e`, package 0.3.1, tags v0.2.0 and
v0.3.1 retained. Development continues on `feat/universal-clients`.

`scripts/test.ps1`: **153 passed**, **92.37% statement coverage**, Ruff passed,
strict mypy passed (24 modules). Python 3.14.7; Windows build 19045. This machine
does not establish Windows 11 acceptance. Log: `.tmp/baseline040.log`.

Read-only `cae broker status --config .cae/broker/broker.json` confirmed the
existing operator broker ready, PID 10268, version 0.3.1. That broker is not a test
fixture and must remain running. Test brokers use separate pipe names and state.

Implemented: independent named-pipe broker, kernel peer PID/SID/image enrollment,
server pinning, protocol v1, policy/quota/audit, seven provider adapters, Python
BrokerClient, optional Control Center, two frozen example applications. Existing
public CAE and BrokerClient interfaces remain compatible. Cloud adapters beyond
the prior OpenAI validation are mock-tested, not live-certified.

Missing at baseline: official C#, C++, Node.js and PowerShell clients; universal
client discovery; cross-language acceptance harness. No clients/ or integration-lab/
directories existed. Later registry hot revocation, routing, installer and service
identity work remain incomplete. Protocol v1 already carries the required initial
client operations, so this milestone does not need a replacement broker or protocol.

Local toolchains include .NET 8/10, Node 26, LLVM 22 and MSVC/Windows SDK. Historical
artifacts remain in dist/ and dist/0.3.1; new client artifacts use dist/0.4.0-clients/.
The retained credential input and production credential entries are not test inputs.
Pre-existing untracked publication reports and user notes are left unchanged.
