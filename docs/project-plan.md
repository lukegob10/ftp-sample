# FTP "Tractor" / "Caterpillar" Engine Project Plan

## 1. Objective
- Build a modular FTP engine ("tractor") capable of hauling heterogeneous workloads (files, streams, metadata jobs) with reliable start/stop and recoverability.
- Provide a composable library core and a service daemon so the engine can be embedded or run standalone.

## 2. Success Criteria
- Sustained transfers at target throughput (define Mbps/Gbps per environment) with <1% failed sessions over rolling 30 days.
- Deterministic resume, retry, and backoff behaviors with idempotent operations.
- Security posture: encrypted control/data where possible, audited auth events, zero critical vulnerabilities in dependency scans.
- Operates under configurable resource budgets (CPU, memory, sockets) and adaptive concurrency.

## 3. Scope
- In scope: FTP/FTPS client and optional server roles, parallel transfers, resumable downloads/uploads, directory sync, checksum validation, pluggable storage backends (local, object store adapter), metrics/exporters, CLI + API surface.
- Out of scope (for now): UI, MFT governance features, SFTP, proprietary extensions, HA clustering beyond active/passive.

## 4. Requirements
- Protocol: RFC 959 baseline plus FTPS (explicit/implicit), passive/active modes, IPv4/IPv6, EPSV/EPRT.
- Transfers: adaptive chunking, restart markers, integrity checks (MD5/SHA-256), temp-file + atomic rename pattern.
- Performance: configurable worker pool, connection pooling, pipelining where safe, zero-copy paths where platform allows.
- Security: TLS 1.2+ with modern ciphers, cert validation/pinning options, secure credential handling (KMS/env), audit logging.
- Reliability: exponential backoff with jitter, circuit breakers for endpoints, deadline/timeout policies, resumable queues.
- Observability: structured logs, metrics (latency, throughput, errors, queue depth), traces over OpenTelemetry, health endpoints.

## 5. Architecture
- Core engine: state machine for session lifecycle; transfer scheduler; retry/resume coordinator; plugin hooks.
- I/O layer: control channel handler, data channel manager, TLS adapter, passive/active negotiator.
- Storage adapters: local filesystem, object store shim, in-memory mock for tests.
- Interfaces: library API, CLI, gRPC/REST facade (pick one), metrics/health endpoints.
- Config system: layered (file/env/flags), hot-reload where feasible.

## 6. Data & Session Models
- Session: endpoint, creds, mode (active/passive), TLS policy, timeouts, restart markers, last-known offsets.
- Transfer job: type (upload/download/sync), source/target URIs, checksum expectations, priority, concurrency limits.
- Queue: persistent job queue with statuses (queued, running, paused, retrying, failed, done) and audit trail.

## 7. Work Breakdown (MVP-first)
1) Skeleton: repo setup, lints/formats, CI, issue templates.  
2) Protocol core: control channel, login, directory/list, binary transfers baseline.  
3) Data path: passive/active negotiator, transfer streams, restart markers.  
4) Resume/retry: checkpointing, backoff policies, idempotent writes.  
5) Storage adapters: local FS, temp-file + atomic rename.  
6) Integrity: checksum support, compare/verify.  
7) Observability: structured logs, metrics, health endpoints.  
8) Security hardening: FTPS, cert validation, secrets handling.  
9) CLI & API surface: job submission, status, pause/resume, config.  
10) Performance tuning: parallelism knobs, pooling, benchmarking.  
11) Docs & samples: quickstart, API usage, ops runbook.

## 8. Testing Strategy
- Unit tests for state machine, retry logic, parsers, and adapters.
- Integration tests against local FTP/FTPS fixtures (active/passive) with chaos (disconnects, slow links).
- Property tests for resume/idempotency; fuzz testing for command parsing.
- Benchmark suite for throughput/latency under varying concurrency.

## 9. Delivery & Timeline (example)
- Week 1: skeleton, control channel, basic transfers.  
- Week 2: restart/resume, temp-file flow, checksum.  
- Week 3: FTPS, observability, CLI/API.  
- Week 4: perf tuning, benchmarks, polish, docs.

## 10. Risks & Mitigations
- Firewall/port constraints (active mode): default to passive, robust negotiation, clear fallbacks.
- Resume edge cases: enforce atomic rename + checksum, property tests.
- TLS variability across servers: configurable cipher suites, downgrade handling, strong defaults.
- Resource exhaustion: circuit breakers, concurrency caps, pooling, backpressure.
- Large directory trees: streaming listings, pagination, parallel traversal with limits.

## 11. Operational Considerations
- Configurable retries/backoff; pausable queues; dead-letter handling.
- Metrics/alerts for failure rate, queue depth, throughput, TLS errors, resource usage.
- Runbook for rotating credentials/certs, log sampling, safe rollbacks.

## 12. Open Questions
- Which API facade is preferred (gRPC vs REST) and hosting model (daemon vs sidecar vs library-only)?
- Priority of server mode vs client-only?
- Target platforms (Linux/Windows) and filesystem constraints?
- Required compliance/regulatory needs for logging/retention?
