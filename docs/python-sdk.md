# Python SDK

Python client SDK for the Memory Governance Protocol.

The canonical install commands, API surface summary, and code examples live in the repository README at `sdk/python/README.md`.

Use that README as the single source of truth for:

- package installation
- synchronous and asynchronous examples
- auth, retry, pagination, and task helpers
- current SDK surface coverage

## What This Page Is For

This page is the short documentation-site entry point for readers deciding whether to use the SDK.

The SDK is the right fit when you want:

- direct Python runtime access to the MGP HTTP surface
- a transport-focused client that is independent of the reference gateway internals
- typed helpers for search, audit, write-candidate, and task flows

## Read Alongside

The SDK makes the most sense when read with:

- `spec/runtime-client.md`
- `spec/runtime-write-candidate.md`
- `spec/http-binding.md`

## Notes

- This SDK is transport-focused and independent of the reference gateway implementation.
- `WriteMemory` can accept either canonical `memory` objects or `MemoryCandidate` payloads via `write_candidate()`.
- Search and get responses in the current `v0.1.0` surface include `consumable_text`, `return_mode`, and `redaction_info`; runtimes should prefer those fields over assuming raw `memory.content` is always prompt-safe.
- The client is designed to align with the HTTP binding and can be used against any gateway that implements the MGP protocol surface.
