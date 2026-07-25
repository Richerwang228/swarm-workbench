# Security Policy

## Supported versions

Security fixes are currently applied to the latest code on `main`. This public
beta has no long-term support promise.

## Report a vulnerability

Do not open a public issue. Use GitHub's **Report a vulnerability** flow in the
Security tab of this repository. Include impact, reproduction steps, affected
commit, and a suggested mitigation if available.

Please allow a reasonable period for triage and remediation before disclosure.
No bounty is offered.

## Deployment warning

Swarm Workbench has no authentication or tenant isolation. Bind it to localhost.
Host shell execution is disabled by default and should remain disabled for
untrusted prompts. See [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md).
