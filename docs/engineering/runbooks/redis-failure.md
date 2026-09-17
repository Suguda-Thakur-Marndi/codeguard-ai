# Operational Runbook: Redis Cache & Broker Failure

**Runbook ID**: `RB-OPS-005`  
**Classification**: Incident Response / Recovery  
**Target Services**: Redis 7 Cache & Message Broker

---

## 1. Symptoms & Alerts

- **Alert**: `RedisConnectionFailure`
- **Symptom**: `/api/v1/health` logs warnings regarding Redis connectivity.
- **Degradation Mode**: CodeGuard AI includes built-in fallback logic (`app/core/redis.py`) that continues processing webhooks synchronously or fails over to database task queuing when Redis is unreachable.

---

## 2. Diagnostic & Recovery Steps

### Step 1: Check Redis Process Status
```bash
docker compose -f infra/docker/docker-compose.prod.yml ps redis
docker compose -f infra/docker/docker-compose.prod.yml logs --tail=100 redis
```

### Step 2: Ping Redis CLI
```bash
docker exec -it codeguard-redis redis-cli ping
# Expected: PONG
```

### Step 3: Check Memory Limits
If Redis was killed due to `maxmemory` exhaustion:
```bash
docker exec -it codeguard-redis redis-cli INFO memory
```

### Step 4: Restart Service
```bash
docker compose -f infra/docker/docker-compose.prod.yml restart redis
```
Verify reconnection:
```bash
curl http://localhost:8000/api/v1/health
# {"status": "healthy", "redis": "connected"}
```
