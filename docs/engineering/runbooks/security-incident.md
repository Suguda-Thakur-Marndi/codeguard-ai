# Operational Runbook: Security Incident Response & Forensics

**Runbook ID**: `RB-OPS-010`  
**Classification**: High-Priority Incident Response  
**Scope**: Token Leaks, Prompt Injections, Sandbox Escapes, Unauthorized Access

---

## 1. Initial Triage & Severity Levels

- **SEV-1 (Critical)**: Active credential compromise, unauthorized review publication, sandbox command breakout.
- **SEV-2 (High)**: Repeated prompt injection attempts causing agent malfunction, unauthorized tenant data access attempt.
- **SEV-3 (Medium)**: Webhook signature verification failure spikes, invalid authentication attempts.

---

## 2. Emergency Containment Procedures

### Step 1: Revoke Compromised GitHub or API Tokens
If a GitHub App private key or Gemini API key is suspected of compromise:
1. Invalidate credential in GitHub App settings or Google Cloud Console immediately.
2. Update environment secret in Vault / Secret Manager.
3. Restart API and Worker containers with updated secret.

### Step 2: Emergency Review Publication Halt
To immediately halt all outgoing GitHub review publications:
```sql
UPDATE organizations SET is_active = false WHERE id = '<tenant_id>';
```
Or pause Celery review publication worker queue:
```bash
docker exec -it codeguard-worker celery -A app.worker control cancel_consumer publication
```

---

## 3. Forensic Investigation & Audit Trail Inspection

CodeGuard AI maintains an immutable, append-only tool execution audit log with automatic secret redaction:
```sql
SELECT id, tool_name, caller_agent, authorization_decision, execution_status, started_at, metadata_json
FROM tool_execution_audits
WHERE authorization_decision = 'BLOCKED' OR execution_status = 'FAILED'
ORDER BY started_at DESC LIMIT 50;
```

Check for prompt injection attempts recorded in review traces:
```bash
docker compose -f infra/docker/docker-compose.prod.yml logs api | grep -i "prompt_injection"
```
