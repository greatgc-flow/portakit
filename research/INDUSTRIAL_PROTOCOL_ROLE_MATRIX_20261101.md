# Industrial protocol candidates — CLIENT / SERVER / SIMULATOR roles (research only)

**Reviewed: 2026-11-01 · No binary admitted, downloaded, executed or bundled.**  
Scope: public-upstream capabilities for optional industrial *test tooling*, **not** evidence that an implementation is complete, safe to bind a socket, compatible with an existing factory application, or approved for company use. This document extends the [2026-10-25 research intake](ENTERPRISE_PORTABLE_REVIEW_20261025.md) without altering the pinned catalog or creating an executable industrial profile.

## 1. Disambiguate three different roles

1. **Protocol application role:** SECS/GEM *HOST* versus *EQUIPMENT*, PLC communications *requester* versus simulated *PLC/device*, OPC UA *client* versus *server*.
2. **TCP transport role:** `ACTIVE` initiates `connect`; `PASSIVE` listens/accepts. **HSMS active/passive does not necessarily mean GEM host/equipment**; an HSMS host can run passive while equipment runs active.
3. **Product role:** A protocol parsing/connection **library** is not necessarily a **ready-to-run device simulator**. A functional simulator also needs memory/tag/variable models, request/response semantics, state transitions, timeouts, multi-client handling, reset rules, safety and deterministic test fixtures.

Conflating any pair creates false "server supported" or "device emulated" claims. All eight candidates below are independent **RESEARCH_ONLY** items for PortaKit; an imported library, online example or checksum match never authorizes an installation.

## 2. Source-evidenced capability matrix

| Candidate | Protocol | Client / initiating work | Incoming server / simulated equipment | Actual role judgment / limit | Source |
| --- | --- | --- | --- | --- | --- |
| **Secs4Net** | SECS-II / HSMS-SS / GEM (.NET) | **Yes**, HSMS active / SECS requests | **HSMS passive supported**, messages can be handled on either end | **Framework, not a finished equipment model.** Active/passive is connection mode, not host/device identity. Upstream current runtime is modern .NET; do not assume VS2015/.NET Framework compatibility | [Project](https://github.com/mkjeff/secs4net), [project file](https://github.com/mkjeff/secs4net/blob/base/src/Secs4Net/Secs4Net.csproj) |
| **secsgem** | SECS/GEM / HSMS (Python) | **Yes**, `GemHostHandler`, active mode | **Yes, configurable**, `GemEquipmentHandler`, passive HSMS, multi-passive support documented | **Reusable host/equipment handlers**, not a universal validated equipment simulator; application supplies equipment model/state and operating policy. Both host/equipment and active/passive must be configured separately | [Upstream](https://github.com/bparzella/secsgem), [HSMS settings](https://secsgem.readthedocs.io/en/stable/reference/hsms/settings.html), [equipment handler](https://secsgem.readthedocs.io/en/v0.0.5/reference/gem/equipmenthandler.html) |
| **pymcprotocol** | Mitsubishi MELSEC MC, 3E/4E (Python) | **Yes**, PC → PLC request/response | **No upstream PLC-listening server capability evidenced** | **CLIENT library, NOT a virtual Mitsubishi PLC server.** Upstream says 3E tested; 4E implemented but not tested (at cited revision). A standalone 3E/4E server must be separately designed and validated | [Official package](https://pypi.org/project/pymcprotocol/), [repository](https://github.com/senrust/pymcprotocol) |
| **python-snap7 / Snap7 Server** | Siemens classic S7 (Python/native API) | **Yes**, S7 client APIs | **Yes**, `snap7.server.Server` / current `s7.Server` test server | **Actual classic S7 test-server component**, not blanket firmware/S7-1200/1500 equivalence. API/runtime and supported S7 services must be checked against the pinned release before adoption | [Official server API](https://python-snap7.readthedocs.io/en/latest/API/server.html), [project](https://github.com/gijzelaerr/python-snap7) |
| **cpppo** | EtherNet/IP CIP subset (Python) | **Yes**, unconnected CIP client | **Yes**, `cpppo.server.enip` simulator | **Limited server and client.** Upstream documents unconnected EtherNet/IP only, not full connected CIP / Logix device fidelity. Do not use its example listener defaults in PortaKit | [Upstream capabilities and limits](https://github.com/pjkundert/cpppo), [server implementation](https://github.com/pjkundert/cpppo/blob/master/server/enip/main.py) |
| **PyXGT** | LS ELECTRIC XGT/FEnet (Python) | **Yes**, PC-to-PLC `plc_ls(...)` client, read/write | **No package server API evidenced** | **CLIENT-focused**; "XGT server" in its description refers to the PLC endpoint. It is not evidence of a PC-side virtual XGT PLC server. Verify exact protocol family (FEnet vs Cnet) before modeling | [PyXGT package](https://pypi.org/project/PyXGT/) |
| **QModMaster** | Modbus RTU/TCP (Qt GUI) | **Yes**, Modbus master/TCP client | **No**, not a Modbus slave simulator | **Client/test-console only**. To test another Modbus master, use a *separate*, approved server/slave implementation; do not equate a GUI client with a virtual device | [Independent vendor how-to](https://support.cognex.com/en/help-articles/how-to-use-qmodmaster-a-free-modbus-client-application), [upstream download](https://sourceforge.net/projects/qmodmaster/) |
| **open62541** | OPC UA (C) | **Yes**, UA client services | **Yes**, OPC UA server APIs | **Client and server SDK**, not a Siemens/Mitsubishi/LS PLC simulator or a prebuilt, enterprise-approved daemon. Compile/packaging, certificate/security policy and application model require separate review | [Upstream](https://github.com/open62541/open62541), [features](https://github.com/open62541/open62541/blob/master/FEATURES.md), [client API](https://open62541.org/doc/master/client.html) |

**Evidence rule:** "no server API evidenced" is **not** proof that no third-party adapter/fork exists. These rows describe the cited project/package directly, not the entire ecosystem, and source/runtime behavior may change between releases. Pin versions and recheck these links before any future source admission.

## 3. Decide based on the side to be simulated (no new binaries required)

| Intended test | Prefer researching | Do **not** mistake for the answer |
| --- | --- | --- |
| Test an equipment-side SECS/GEM implementation against a synthetic host | secsgem host handler or Secs4Net host code, with explicit HSMS connection direction | A raw TCP listener alone is not a compliant GEM host |
| Test a host/CIM SECS interface against synthetic equipment | secsgem equipment handler with controlled GEM state + HSMS; Secs4Net with a separate equipment model | Treating active/passive as an equipment/host role selector |
| Test an S7-speaking PC client without a real PLC | python-snap7 classic S7 test server in a separately approved lab | Any S7 API being equivalent to full Siemens PLC firmware |
| Test an EtherNet/IP client with a synthetic tag set | cpppo's documented **unconnected** CIP server subset | Full connected CIP / device safety / broad PLC emulation |
| Test a Mitsubishi MC 3E/4E client against a virtual PLC | A **separately reviewed MC server implementation** (outside PortaKit candidate client libraries) | `pymcprotocol` client library acting as server |
| Test an LS XGT client against a virtual XGT device | A **separately reviewed XGT server implementation** | `PyXGT` PC client connecting to a real PLC |
| Test a Modbus slave/device by sending read/write requests | QModMaster client GUI, subject to end-user approval | QModMaster pretending to be the Modbus slave |
| Test an OPC UA client against local data variables | open62541 server with a synthetic information model | Claims of vendor PLC-protocol or actual PLC memory equivalence |

For independent virtual devices, a separate process per simulated device is a sensible **optional architecture**, not a default start action in PortaKit. Address, port, protocol version, clock/timing policy, memory model and external binding must all remain explicit configuration, **never copied from illustrative examples into active listeners**.

## 4. Fail-closed lab design for any future server implementation

**Default: no network listener, no device writes, no driver/service creation.** Start by validating only isolated parser/response functions on in-memory synthetic frames. Later, a **final-user-approved** nonproduction harness may opt in to loopback (`127.0.0.1`); remote binding must require a separate, explicit approval and never be enabled automatically by a portable tool profile.

Minimum independent gates for a simulator *before* a new code implementation is considered complete:

- **Framing and strict limits:** length prefixes, checksums, transaction IDs, endianness, protocol version, bounded frame/queue/clients/memory; reject zero/oversized/malformed/truncated/duplicate frames without state corruption.
- **Timed transport:** configurable connect/accept/read/write/idle/response/retry timeouts; no unbounded blocking, spin loops, or infinite reconnect storms. Include half-open peers and deterministic shutdown.
- **Simulation semantics:** explicitly declared address/register/tag model, read versus write permissions, initial/reset values, multi-client concurrency and write-conflict policy, diagnostic error replies.
- **Evidence and reality boundaries:** independent synthetic unit/integration tests, stdout-identical local logging, no credentials/internal addresses, no live factory traffic; source CI proves *only* source behavior.
- **Independent release and site controls:** immutable original source/license/notice, company-use and separate redistribution/transfer/EDR approvals, real Windows runtime/GUI/performance and deployment choice are **final-user/organization responsibilities** per [acceptance policy](../docs/END_USER_ACCEPTANCE.md).

## 5. Legacy runtime compatibility (NOT_VERIFIED unless checked at exact release)

- **Secs4Net:** current upstream modern .NET targets are not a drop-in for Visual Studio 2015 / .NET Framework; don't suggest automatic compatibility.
- **secsgem / pymcprotocol / python-snap7 / cpppo / PyXGT:** Python packages or native wrappers, **not** Java JDK 8 or PowerShell 2.0 / 5.x components. Their Windows, Python version, dependency, ABI and company policy requirements need per-version verification.
- **QModMaster:** Qt GUI with build-specific runtime needs, not a headless Modbus server.
- **open62541:** C SDK with platform plugins. Do not claim a specific VS2015 build, compiler, crypto backend or certificate compatibility without an isolated build test.
- **None** of the eight is silently enrolled in `catalog.json`, `toolsets.json` or a pinned deployment workflow. The live **151 software-option** inventory and **19 SHA-pinned tools** are unchanged by this document.

**Next technical action:** if a concrete server candidate is selected later, create a *separate source/test issue* for exactly one protocol and one device role, with bounded synthetic positive/negative cases and no vendor binary distribution. Final-user tests and enterprise permission are distinct independent handoffs, not prerequisites for reviewing this research documentation.
