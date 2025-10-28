# Incident Playbook: Production Outage Caused by Security Breach

## Severity & Ownership
- Severity: SEV-1
- Incident Commander (IC): On-call SRE
- Security Lead: On-call Security Engineer
- Comms Lead: Eng Manager or PR (if external impact)

## Immediate Actions (T+0–15m)
1. IC declares SEV-1 and starts incident bridge (Slack #inc-sev1 + Zoom).
2. Security Lead initiates containment: isolate affected hosts, revoke suspected creds/tokens.
3. Freeze deploys; enable WAF block rules as needed.

## Triage (T+15–60m)
4. Identify blast radius (services, data, accounts).
5. Switch to safe failover if possible; restore minimal service.
6. Enable elevated logging; snapshot affected systems for forensics.

## Escalation Path
- IC → Director of Engineering (10 min if unresolved)
- Security Lead → Head of Security (immediately on confirmed breach)
- If customer data at risk → Legal & Privacy (within 60 min)
- If > 1h outage or regulatory impact → Exec Bridge (CEO/CTO)

## Communication
- Internal updates every 15 min on bridge; status page if customer impact > 30 min.
- Draft customer comms with Legal/PR once facts are confirmed.

## Evidence & Forensics
- Preserve logs, DB query history, auth events, and disk snapshots.
- Do not reboot compromised hosts until snapshots complete.

## Recovery
- Rotate affected secrets/keys; verify integrity before reintroducing nodes.
- Post-incident hardening: rules, detections, tabletop.

## Exit Criteria
- Service stable ≥ 1h, containment confirmed, no active threat.

## Postmortem
- Within 72h: blameless write-up, action items with owners & due dates.
