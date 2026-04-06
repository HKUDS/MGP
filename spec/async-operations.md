# Async Operations

This document defines the minimal async task model for `MGP Base Protocol`.

## Purpose

Some MGP operations may become too large or slow to assume a single immediate HTTP response.

The first async profile provides:

- async task handles
- polling-based task inspection
- task cancellation
- machine-readable progress shape

The initial focus is on interoperability operations such as:

- `ExportMemories`
- `ImportMemories`
- `SyncMemories`

## Execution Modes

Operations that support async behavior may accept:

- `execution_mode = "sync"`
- `execution_mode = "async"`

Reference behavior:

- if omitted, execution remains synchronous
- if `execution_mode = "async"`, the server may accept the request and return a task handle

## Async Task Object

Machine-readable schema:

- `schemas/async-task.schema.json`

The task object includes:

- `task_id`
- `operation`
- `status`
- `request_id`
- `created_at`
- `updated_at`
- `progress`
- `total`
- optional `message`
- optional `result`
- optional `error`

## Task Status

Allowed terminal and non-terminal states:

- `pending`
- `running`
- `completed`
- `failed`
- `cancelled`

Reference behavior:

- `pending` means accepted but not yet completed
- `running` means work has begun
- `completed` means `result` is available
- `failed` means `error` is available
- `cancelled` means the task will not produce a normal result

## Progress Shape

Machine-readable schema:

- `schemas/progress-event.schema.json`

The initial async profile does not require push notifications for progress.

Instead:

- implementations may surface progress through task polling
- later profiles may add streaming progress or notifications

## Task Polling

Task state is polled through:

- `POST /mgp/tasks/get`

Machine-readable schemas:

- `schemas/get-task.request.schema.json`
- `schemas/get-task.response.schema.json`

## Task Cancellation

Task cancellation is requested through:

- `POST /mgp/tasks/cancel`

Machine-readable schemas:

- `schemas/cancel-task.request.schema.json`
- `schemas/cancel-task.response.schema.json`

Reference behavior:

- cancellation is best-effort
- cancelling a terminal task returns the current terminal state
- cancelling a non-existent task should return a canonical task-not-found error

## Initial Reference Profile

The reference gateway currently implements a minimal polling profile:

- async tasks are supported for `export`, `import`, and `sync`
- progress is exposed through the task object rather than push delivery
- tasks can be cancelled before completion
- push notifications are still out of scope

## Non-Goals

This document does not yet define:

- server-sent progress streams
- resumable event streams
- task authorization model
- durable task persistence across process restarts
