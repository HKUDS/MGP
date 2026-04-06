# Security Policy

## Supported Scope

Security issues are relevant for:

- the reference gateway in `reference/`
- the published Python SDK in `sdk/python/`
- protocol contract assets in `spec/`, `schemas/`, and `openapi/`

## Reporting A Vulnerability

Please avoid opening a public issue for unpatched vulnerabilities.

Instead:

1. Prepare a private report describing the affected path, impact, and reproduction steps.
2. Include the relevant protocol version, gateway/SDK version, and deployment assumptions.
3. Share the report with the project maintainer through a private channel before public disclosure.

## What To Include

Helpful reports usually include:

- affected file paths or package names
- exact configuration or environment assumptions
- whether the issue affects the protocol contract, the reference gateway, the SDK, or all three
- proof of concept requests, payloads, or logs when safe to share

## Disclosure Guidance

- do not publish credentials, private keys, or tenant data in reports
- give the maintainer time to reproduce and patch before public discussion
- treat third-party provider issues separately when they originate in an external service rather than MGP itself
