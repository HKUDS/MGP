# Glossary

## memory object

A memory object is the canonical unit of governed memory exchanged through MGP.

Example: A stored user preference such as "prefers concise answers" is one memory object.

## subject

A subject is the entity that a memory is about or attached to, such as a user, agent, organization, task, or session.

Example: A preference linked to user `u_123` has that user as its subject.

## scope

Scope defines the boundary within which a memory is valid, visible, or intended to apply.

Example: A memory with `session` scope should not be treated as a durable user-wide fact.

## type

Type identifies the semantic class of a memory object.

Example: A remembered user preference and a recorded episodic event are different memory types.

## policy context

Policy context is the request-side metadata that explains who is acting, on whose behalf, for what task, and under what governance constraints.

Example: A write request can include the acting agent, tenant, risk level, and task identifier as policy context.

## retention

Retention describes how long a memory should remain available before review, expiration, or deletion rules apply.

Example: A session-bound memory may have short retention while a verified user profile fact may be persistent.

## expiration

Expiration is the protocol event or state transition in which a memory is no longer considered active because its validity or retention window has ended.

Example: A task-scoped memory may expire automatically after the task is closed.

## revocation

Revocation is the explicit withdrawal of a memory from normal use, regardless of its original retention period.

Example: A user may revoke a previously stored preference after correcting it.

## supersede

To supersede a memory is to replace it with a newer or more authoritative memory while preserving the relationship between them.

Example: A corrected home city memory can supersede an earlier incorrect city value.

## conflict

A conflict occurs when two or more memories cannot be accepted together without clarification, ordering, or coexistence rules.

Example: Two memories for the same subject that claim different birthdays represent a conflict.

## lineage

Lineage records how a memory was created, derived, changed, or related to other memories over time.

Example: A summary memory derived from a conversation transcript should retain a lineage link to its source.

## adapter

An adapter maps a concrete backend's native model and behavior into MGP-compatible contracts.

Example: A file-backed adapter can translate markdown notes into canonical memory objects.

## capability

A capability is a declared feature that tells runtimes what an adapter or backend can and cannot do under MGP.

Example: A backend may declare that it supports search but not native TTL.

## runtime

A runtime is the agent-side system that calls MGP operations while executing tasks on behalf of users or other subjects.

Example: An agent runtime can use MGP to recall and commit governed memory.

## backend

A backend is the concrete storage or memory system that ultimately persists or serves memory data.

Example: A graph database, vector database, or file-based store can each act as a backend behind MGP.
