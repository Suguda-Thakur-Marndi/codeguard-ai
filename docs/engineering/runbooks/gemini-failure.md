# Operational Runbook: Gemini AI Provider Outage & Rate Limiting

**Runbook ID**: `RB-OPS-007`  
**Classification**: AI Provider Incident  
**Target Services**: Gemini Provider Adapter (`apps/api/app/agents/llm/gemini.py`)

---

## 1. Symptoms & Alerts

- **Alert**: `GeminiAPIError` / `GeminiRateLimit429`
- **Symptom**: Review jobs in LangGraph orchestrator timeout or fail at `specialists_executed` stage.
- **Log Pattern**: `GoogleGenAIError: Resource has been exhausted (e.g. check quota)` or `HTTP 503 Service Unavailable`.

---

## 2. Automated Circuit Breaking & Resilience

CodeGuard AI provides built-in resilience against AI provider fluctuations:
1. **Model Tier Fallback**: If `gemini-2.5-pro` experiences rate limiting or high latency, the router falls back to `gemini-2.5-flash`.
2. **Deterministic Mock Mode**: In development or offline simulation environments, `CODEGUARD_BENCHMARK_MODE=true` routes all requests through `MockLLMProvider` without contacting Google Cloud APIs.
3. **Exponential Backoff**: Transient network drops are retried up to 3 times with exponential backoff (base 2.0s).

---

## 3. Incident Recovery Steps

### Step 1: Verify Google Cloud Quota & API Key Status
```powershell
curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"
```

### Step 2: Emergency Model Tier Reconfiguration
If a specific Gemini model is deprecated or experiencing an outage, modify `app/core/config.py` or runtime environment variables:
```bash
# Temporarily re-point reasoning tier to alternate stable model
export GEMINI_MODEL_FAST="gemini-2.5-flash"
export GEMINI_MODEL_REASONING="gemini-2.5-flash"
```
Restart backend containers:
```bash
docker compose -f infra/docker/docker-compose.prod.yml restart api worker
```
