# Material 05: Submission Packet (English Summary)

> Companion to the Chinese materials (01–04). Mandol is the team's own
> self-developed memory system; this entry is its competition adaptation
> (Add/Search wrapper) developed in a dedicated fork. Fill `*[TBD]*` fields
> before submission; keep consistent with the actual deployment and the frozen
> commit/tag.

## 1. Identity & System

| Field | Value |
| --- | --- |
| Challenge | Agent Memory Challenge / Agent Memory Leaderboard (AML), 2nd cycle |
| System name | Mandol-AML |
| Version | 0.1.0-aml.1 (freeze via git tag at submission) |
| Project nature | Self-developed system Mandol + competition adaptation layer (core unchanged) |
| Track | Textual Memory + Coding Agent Memory |
| Division | Open-source methods (Academic methods) |
| Route | Self-hosted Add/Search API (public repo + frozen version) |
| Organization / team | *[TBD: university / lab]* |
| Contact / email | *[TBD]* |

## 2. Code & Reproducibility

| Field | Value |
| --- | --- |
| Competition repo (public) | https://github.com/bubaa9531-dh/Mandol |
| Main development repo | https://github.com/AgentCombo/Mandol (self-developed Mandol, Apache-2.0) |
| Repo relation | The competition repo is a fork of the main development repo for independent competition development; core code unchanged |
| Paper | Mandol: An Agglomerative Agent Memory System for Long-Term Conversations — https://arxiv.org/abs/2606.29778 |
| Paper authors | Yuhan Zhang, Zhiyuan Guo, Ziheng Zeng, Wei Wang, Wentao Wu, Lijie Xu (per arXiv page) |
| Sync baseline with main repo | `6d7af4f…` |
| Adapter code commit | `b4dc454149a29b34e669e73291d2e944e557f080` |
| Frozen tag at submission | `v0.1.0-aml.1` (tag the latest main before the formal run) |
| Changes vs main repo | Only additive files (`src/mandol_aml/`, Dockerfile, compose, env template, docs, tests, scripts); Mandol core unchanged. See aml/CHANGES.md and aml/ATTRIBUTION.md. |

## 3. Endpoints (self-hosted)

| Endpoint | Notes |
| --- | --- |
| `POST https://*[TBD: domain]*/add` | Synchronous write; HTTP 200 only after data is stored and immediately searchable; echoes `request_id/user_id/session_id` |
| `POST https://*[TBD: domain]*/search` | Returns `{"data":[{id, content, score?, created_at?}]}` ordered by relevance, count <= top_k |
| `GET https://*[TBD: domain]*/health` | Unauthenticated; any 2xx = healthy (platform checks `/health` on the Add origin if no custom URL) |
| Auth | Memory System Key: `Authorization: Bearer/Token <key>` or `X-Api-Key: <key>`; unauthenticated allowed only for public smoke |

Contract details follow the official API guide: https://agentmemoryleaderboard.ai/api-guide

## 4. Capacity / Timeouts / Rate Limit (declare actual values)

- Add target latency budget: 60 s (`AML_ADD_TIMEOUT_SECONDS`); Search: 30 s (`AML_SEARCH_TIMEOUT_SECONDS`); enforce hard timeouts at gateway.
- Write throughput: >= 10 QPS per instance (higher with batched Add); search throughput >= 10 QPS.
- Rate limit: unlimited by default (`AML_RATE_LIMIT_RPM=0`); set and declare if applied (429 + Retry-After on exceed).
- Instance: *[TBD: e.g., 8 vCPU / 16–32 GB, public HTTPS endpoint]*.
- Availability: 2026-09-20 → 2026-11-04, stable and publicly reachable; no contract/auth/capacity changes after the formal run is accepted.

## 5. Compliance Highlights

- `user_id` is the only retrieval-isolation boundary; `session_id` is metadata only; no cross-user retrieval.
- Search returns memory evidence only; it never produces final answers.
- Evaluation data is used only for the current job; not for training/fine-tuning/redistribution; deleted within 30 days (`AML_DATA_TTL_DAYS=30`).
- No hard-coded answers, no benchmark leakage, no prompt injection, no live human answering, no undisclosed code reuse.
- No secrets in the public repository (Memory System Key and provider keys are set only in the deployment environment; to be provided by the project PI).

## 6. Key Dates (2nd cycle, UTC+8)

- 2026-09-20: registration opens (apply/bind key at https://agentmemoryleaderboard.ai/evaluation)
- 2026-10-31 23:59: submission deadline
- 2026-11-04 23:59: evaluation queue ends (keep endpoints available)
- Mid-Nov: results released after qualification & compliance review

## 7. Local Materials Index

- Chinese form/method/API/compliance materials: aml/docs/01–04
- Ownership & citation: aml/ATTRIBUTION.md; change disclosure: aml/CHANGES.md
- Service README: aml/README.md; overlay README: README_AML_OVERLAY.md
- Smoke client: aml/scripts/smoke_test.py; contract tests: tests/test_contract.py
