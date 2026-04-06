# Runtime Write Candidate

This document defines the runtime-side candidate contract that sits before canonical `WriteMemory`.

## Purpose

An agent runtime often knows that something is worth remembering before it knows the exact canonical memory object shape.

MGP standardizes that intermediate stage as a `MemoryCandidate` so runtimes can:

- extract memory in a shared shape
- attach source evidence before canonicalization
- express dedupe or merge intent explicitly
- hand off candidate resolution to a gateway or adapter

## Candidate Shape

Machine-readable schema:

- `schemas/memory-candidate.schema.json`

Minimum fields:

- `candidate_kind`
- `subject`
- `scope`
- `proposed_type`
- `statement`
- `source`

Common optional fields:

- `content`
- `source_evidence`
- `confidence`
- `sensitivity`
- `retention_policy`
- `ttl_seconds`
- `merge_hint`
- `extensions`

## Candidate Kinds

- `assertion` — runtime believes a stable memory was asserted
- `confirmation` — runtime is reinforcing or confirming existing memory
- `correction` — runtime is correcting prior memory
- `derived` — runtime or tool synthesized the candidate from evidence

## Mapping to Canonical Memory

Typical mapping:

- `subject` -> `memory.subject`
- `scope` -> `memory.scope`
- `proposed_type` -> `memory.type`
- `statement` -> `memory.content.statement`
- `source` -> `memory.source`
- `source_evidence` -> `memory.evidence` / `memory.evidence_refs`
- `candidate_kind` -> `memory.assertion_mode`
- `merge_hint` -> gateway-side dedupe / upsert / merge logic

## Merge Guidance

Machine-readable schema:

- `schemas/memory-merge-hint.schema.json`

Typical strategies:

- `create`
- `dedupe`
- `upsert`
- `replace`
- `merge`
- `reinforce`
- `manual_review_required`

## Reference Usage

The reference gateway accepts either:

- a canonical `memory` object
- a `candidate` object that it converts to canonical memory before write

This allows runtimes to start with candidates while still preserving a stable write surface.
