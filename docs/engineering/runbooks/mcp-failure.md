# Operational Runbook: Model Context Protocol (MCP) Server Outage

**Runbook ID**: `RB-OPS-008`  
**Classification**: Tool Governance Incident  
**Target Services**: FastMCP Daemon (`apps/mcp-server`), Sentinel Policy Engine

---

## 1. Symptoms & Alerts

- **Alert**: `MCPServerUnreachable`
- **Symptom**: Tool validation checks fail with `Connection refused` to `http://localhost:8001` or standard input/output stream closes unexpectedly.
- **Log Pattern**: `MCPClientError: Failed to communicate with tool server`.

---

## 2. Diagnostic Procedure

### Step 1: Check MCP Process Status
```bash
docker compose -f infra/docker/docker-compose.prod.yml ps mcp-server
docker compose -f infra/docker/docker-compose.prod.yml logs --tail=100 mcp-server
```

### Step 2: Test MCP Health Endpoint
```bash
curl http://localhost:8001/health
# Expected: {"status": "ok"}
```

### Step 3: Verify Tool Schemas via Discovery Endpoint
```bash
curl http://localhost:8001/mcp/tools
```

---

## 3. Mitigation & Recovery Steps

### Step 1: Restart MCP Daemon
```bash
docker compose -f infra/docker/docker-compose.prod.yml restart mcp-server
```

### Step 2: Validate Sentinel Policy Integrity
Ensure that Sentinel policy blocks remain enforced after restart:
```powershell
.\.venv\Scripts\python.exe -m pytest apps/mcp-server/tests/test_mcp_policy.py -v
```
All 9 forbidden operations (`execute_shell`, `eval_code`, etc.) must report blocked.
