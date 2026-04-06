# Conflicts

This document defines the conflict model for MGP.

## Purpose

A conflict occurs when two or more memory objects cannot be accepted together without an explicit protocol rule, ordering rule, or human review step.

Conflict handling is a protocol concern because different backends may detect or represent contradictions differently. MGP standardizes the semantics visible to runtimes even when backend implementations vary.

## Conflict Types

### Same Subject, Same Fact Key, Different Value

This conflict occurs when two memories describe the same fact slot for the same subject but with incompatible values.

Example:

- subject: `user_123`
- fact key: `preferred_language`
- value A: `English`
- value B: `Japanese`

`fact key` is a conceptual comparison slot, not a canonical top-level field in the memory object schema. Implementations may derive it from structured `content`, merge hints, or documented adapter-specific conventions, but they should not assume a universal protocol field named `fact_key`.

### Overlapping Validity Window

This conflict occurs when two memories that should be temporally distinct claim overlapping `valid_from` and `valid_to` windows in a way that creates ambiguity.

Example:

- one relationship memory claims employment at Company A through June
- another conflicting employment memory claims employment at Company B during the same period

### Lower-Confidence Replacement

This conflict occurs when a new memory attempts to replace or supersede an existing memory despite having lower confidence or weaker evidence.

Example:

- existing memory confidence: `0.92`
- incoming replacement confidence: `0.41`

### Cross-Source Contradiction

This conflict occurs when memories from different source categories or source references disagree in a way that cannot be ignored.

Example:

- human-confirmed profile fact says the user lives in Berlin
- tool-imported document says the user lives in Paris

## Conflict Resolution Modes

### `latest_wins`

The memory with the newest authoritative timestamp takes precedence.

Use when:

- newer data is generally more trustworthy
- the domain tolerates replacing older values

Example:

Two profile updates disagree, and the system keeps the one with the latest `updated_at`.

Response implication:

- the winning memory remains active
- the losing memory may be marked as superseded
- a lineage link such as `supersedes` should be recorded when possible

### `source_priority`

The memory from the highest-priority source wins according to implementation-defined source ordering.

Use when:

- human-entered data should override inferred data
- some system sources are treated as authoritative

Example:

`human` source overrides `external` source for a user preference conflict.

Response implication:

- the response should return the selected memory outcome
- audit data should record the applied source-priority rule

### `confidence_weighted`

The memory with the higher confidence wins.

Use when:

- confidence is meaningful and comparable across the conflicting memories
- the implementation can justify numeric ranking

Example:

A semantic fact with confidence `0.88` overrides the same fact at confidence `0.45`.

Response implication:

- the chosen memory is returned as active
- the losing memory may remain as historical lineage depending on implementation policy

### `coexist_with_validity_window`

Both memories are preserved, but their validity ranges must be interpreted as temporally segmented rather than simultaneously true.

Use when:

- the contradiction can be resolved by time slicing
- the domain is temporal and multiple versions are expected

Example:

Two address memories are both valid, but one covers a previous time range and the other starts later.

Response implication:

- both memory objects may remain present
- callers should receive validity metadata sufficient to distinguish them

### `manual_review_required`

The system records the conflict but does not resolve it automatically.

Use when:

- the conflict is high risk
- the evidence is ambiguous
- incorrect resolution would be more harmful than delayed resolution

Example:

Two high-confidence, cross-source identity facts disagree and neither can be safely preferred.

Response implication:

- the operation may return `MGP_CONFLICT_UNRESOLVED`
- audit data should indicate review is required
- a `conflicts_with` lineage relation should be recorded when possible

## Detection Guidance

Implementations should consider conflict checks during:

- `WriteMemory`
- `UpdateMemory`
- background consolidation or governance review

Conflict handling is also influenced by explicit merge guidance:

- `dedupe`
- `upsert`
- `replace`
- `merge`
- `reinforce`
- `manual_review_required`

Not every backend must detect conflicts natively. Adapters and gateways may perform protocol-level checks before or after backend writes.

## Response and Error Behavior

When a conflict is automatically resolved:

- the response may still return `status: ok`
- the resulting memory state should reflect the selected resolution mode
- the response should expose a `resolution` value where possible

When a conflict is not automatically resolved:

- the response should return `status: error`
- the error code should be `MGP_CONFLICT_UNRESOLVED`

## Lineage Implications

Conflict handling should produce lineage where possible:

- `supersedes` for successful replacement
- `conflicts_with` for unresolved contradiction
- `derived_from` when a consolidated memory is produced from multiple inputs

## Dedupe and Reinforcement Guidance

Two incoming memories may not be in conflict at all if the runtime explicitly signals:

- a shared dedupe key
- reinforcement intent
- a safe merge strategy

Examples:

- same user preference repeated later with stronger evidence -> `reinforce`
- same fact reasserted with identical statement -> `dedupe`
- same key but changed value -> `replace` or `manual_review_required` depending on risk

## Non-Goals

This document does not define:

- backend-specific fact key extraction algorithms
- confidence calculation formulas
- universal source authority ordering
