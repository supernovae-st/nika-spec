# Security Policy

This repository carries the **Nika workflow language specification** and
its conformance tooling (`conformance/runner.py` · fixtures · JSON schema).
Security-relevant surface here · the published JSON schema consumed by
editors/CI, and the conformance runner executed against untrusted
workflow files.

## Supported Versions

The spec is pinned at the `nika: v1` contract · additions are additive
within v1. Only the latest tagged release and `main` receive fixes.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub
issues, discussions, or pull requests.**

Send an email to **security@supernovae.studio** with ·

- A description of the issue (e.g. a fixture/schema input that crashes or
  bypasses the conformance oracle · a schema served with unsafe defaults)
- Steps to reproduce or a minimal proof-of-concept
- The commit SHA or tag where you observed it

We acknowledge receipt within **72 hours** and aim for a substantive
response (initial triage + ETA) within **7 days**.

## Disclosure Process

1. **Triage** · maintainers verify the report and confirm the scope
2. **Fix development** · patch authored privately
3. **Public release** · GitHub Security Advisory + CHANGELOG entry
4. **Credit** · reporter named in the advisory unless anonymity is requested

We aim for **≤90 days** between report and public disclosure, shorter for
actively-exploited issues.
