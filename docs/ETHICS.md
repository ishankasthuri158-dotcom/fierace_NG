# Ethics & Authorized Use

Fierce-NG is a security research and authorized-penetration-testing tool. Using
it against infrastructure you do not own or have **explicit written permission**
to test may be illegal in your jurisdiction.

## Rules of engagement

- **Authorization & scope.** Only scan assets covered by explicit written
  consent (your own lab, or a bug-bounty / pentest scope that permits scanning).
  Respect the terms of service of every OSINT API you enable (crt.sh, Shodan).
- **Non-disruption.** Fierce-NG defaults to conservative QPS and jitter, rotates
  resolvers, and automatically backs off when error rates spike. Do not raise
  `--qps` beyond what the target and your authorization allow. The tool never
  exploits findings — it only observes.
- **Privacy & data minimization.** Collect only technical DNS/CT metadata. Do
  not collect or store personal data. Secure and access-log any stored results.
- **Responsible disclosure.** Communicate verified high-risk findings (e.g.
  dangling CNAMEs, zone-transfer exposure) to the asset owner through agreed
  channels before any public discussion.
- **Auditability.** Every run produces a signed manifest (set
  `FIERCE_NG_SIGNING_KEY`) with input hashes so experiments are reproducible and
  attributable.

## What Fierce-NG will not do

It does not brute-force credentials, exploit vulnerabilities, perform
denial-of-service, or attempt to take over discovered resources. It maps and
scores the attack surface so a human analyst can act responsibly.
