# ADR 0008: Bounded acquisition transport

- Status: Accepted
- Date: 2026-10-11
- Decision owners: Aegis maintainers

## Context

Provider adapters used different HTTP clients, redirect behavior, body limits, and retry rules. Initial URL validation did not guarantee that redirect targets were safe, and provider `Retry-After` guidance could not reach operation-health decisions.

## Decision

Public HTTP acquisition uses `backend.infrastructure.acquisition.network.http.fetch_public_http` at the adapter boundary. It permits GET only, validates the initial URL, every redirect, and the final URL, strips authorization on cross-origin redirects, requests identity encoding, bounds response bytes and redirects, and retries only transient status/network failures with bounded exponential backoff and jitter. Deterministic authentication or policy failures are not retried. Provider status, attempt count, endpoint, and bounded `Retry-After` values flow into operation telemetry.

Browser rescue remains available for web pages, but every HTTP(S) browser request is checked before transmission and rendered output is size bounded. A 429 is never bypassed with a browser fallback.

## Consequences

- GitHub REST, V2EX, RSS, podcast syndication, web reading, and Jina reading share one transport-safety policy.
- Provider parsing and evidence normalization remain adapter responsibilities.
- Runtime observations remain process-local. Multi-worker convergence requires an external observation store in a later phase; none was added for v1.
- External tools such as `yt-dlp` expose protocol facts only when those facts are actually observable.

