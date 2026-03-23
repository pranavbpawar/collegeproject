# TBAPS Deployment Checklist

Run these commands after deployment to validate every component.

---

## 1. System Services

```bash
for svc in postgresql redis-server rabbitmq-server nginx openvpn-server@server; do
    echo -n "$svc: "
    systemctl is-active $svc && echo "✅ running" || echo "❌ STOPPED"
done

for svc in tbaps-api tbaps-worker tbaps-capture; do
    echo -n "$svc: "
    systemctl is-active $svc && echo "✅ running" || echo "❌ STOPPED"
done
```

---

## 2. API Health

```bash
# Liveness
curl -sf http://localhost:8000/health | python3 -m json.tool
# Expected: {"status": "ok", ...}

# Readiness (checks DB + Redis)
curl -sf http://localhost:8000/readiness | python3 -m json.tool
# Expected: {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}
```

---

## 3. Database

```bash
# Connection
psql -U ztuser -d zerotrust -h localhost -c "SELECT version();"

# TimescaleDB extension
psql -U ztuser -d zerotrust -h localhost -c "SELECT extname, extversion FROM pg_extension WHERE extname='timescaledb';"

# Table count (expect 20+)
psql -U ztuser -d zerotrust -h localhost -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
```

---

## 4. Redis

```bash
redis-cli ping          # PONG
redis-cli info server | grep redis_version
```

---

## 5. RabbitMQ

```bash
sudo rabbitmqctl status | grep -E "RabbitMQ|Erlang"
sudo rabbitmqctl list_vhosts
sudo rabbitmqctl list_users
```

---

## 6. Celery Worker

```bash
# Check worker is connected to broker
/opt/tbaps/venv/bin/celery --app app.core.celery_app.celery_app inspect ping \
    --workdir /opt/tbaps/backend
# Expected: {"tbaps-worker@hostname": {"ok": "pong"}}
```

---

## 7. Nginx + Frontend

```bash
# Config test
sudo nginx -t

# HTTP → HTTPS redirect
curl -sI http://localhost/ | grep -E "HTTP|Location"
# Expected: 301 redirect to https://

# Frontend loads
curl -sk https://localhost/ -o /dev/null -w "%{http_code}"
# Expected: 200
```

---

## 8. No Docker References Remain

```bash
grep -r "docker\|container_name\|POSTGRES_HOST=postgres\|redis://redis" \
    /home/kali/Desktop/MACHINE \
    --include="*.py" --include="*.env" --include="*.yml" --include="*.sh" \
    --exclude-dir=".git" 2>/dev/null
# Expected: no output
```

---

## 9. Config Loads Correctly

```bash
cd /opt/tbaps/backend
source /opt/tbaps/venv/bin/activate
python -c "
from app.core.config import settings
print('APP_ENV:', settings.APP_ENV)
print('DATABASE_URL:', settings.DATABASE_URL[:30] + '...')
print('REDIS_URL:', settings.REDIS_URL)
print('RABBITMQ_URL:', settings.RABBITMQ_URL[:30] + '...')
print('Config OK ✅')
"
```

---

## 10. Log Verification

```bash
# API logs (JSON structured)
sudo journalctl -u tbaps-api --since "5 minutes ago" | tail -20

# No ERROR or CRITICAL in last hour
sudo journalctl -u tbaps-api --since "1 hour ago" | grep -c "ERROR\|CRITICAL" || echo "0 errors ✅"
```

---

## All-in-One Health Script

```bash
cat > /tmp/tbaps-health.sh << 'EOF'
#!/bin/bash
echo "=== TBAPS System Health ==="
PASS=0; FAIL=0
check() {
    if eval "$2" &>/dev/null; then echo "✅ $1"; ((PASS++))
    else echo "❌ $1"; ((FAIL++)); fi
}
check "PostgreSQL"    "systemctl is-active postgresql"
check "Redis"         "redis-cli ping | grep -q PONG"
check "RabbitMQ"      "systemctl is-active rabbitmq-server"
check "Nginx"         "systemctl is-active nginx"
check "tbaps-api"     "systemctl is-active tbaps-api"
check "tbaps-worker"  "systemctl is-active tbaps-worker"
check "tbaps-capture" "systemctl is-active tbaps-capture"
check "API /health"   "curl -sf http://localhost:8000/health"
check "API /readiness" "curl -sf http://localhost:8000/readiness | grep -q ready"
echo ""
echo "Passed: $PASS | Failed: $FAIL"
EOF
bash /tmp/tbaps-health.sh
```
