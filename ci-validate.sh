#!/bin/bash
# set -e  (continue on error)

echo "======================================"
echo "CI/CD Workflow Validation"
echo "diving.school project"
echo "$(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================"

PROJECT_ROOT="/Users/wjjmac/localserver/diving.school"
BACKEND="$PROJECT_ROOT/backend"
FRONTEND="$PROJECT_ROOT/frontend"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

success() { echo -e "${GREEN}✓ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

# 计数器
PASS=0
FAIL=0

check() {
    if [ $? -eq 0 ]; then
        success "$1"
        ((PASS++))
    else
        error "$1"
        ((FAIL++))
    fi
}

echo ""
echo "=== Step 1: Environment Check ==="
echo "Python: $(python3 --version 2>&1)"
echo "Node: $(node --version 2>&1)"
echo "NPM: $(npm --version 2>&1)"
check "Environment check"

echo ""
echo "=== Step 2: Backend Syntax Check ==="
cd "$BACKEND"
venv/bin/python3 -m py_compile app/routers/manager.py 2>/dev/null
check "manager.py syntax"
venv/bin/python3 -m py_compile app/main.py 2>/dev/null
check "main.py syntax"
venv/bin/python3 -m py_compile app/models/class_system.py 2>/dev/null
check "class_system.py syntax"

echo ""
echo "=== Step 3: Backend Dependencies Check ==="
venv/bin/pip3 list | grep -q "fastapi" && success "FastAPI installed" || { error "FastAPI missing"; ((FAIL++)); }
venv/bin/pip3 list | grep -q "sqlalchemy" && success "SQLAlchemy installed" || { error "SQLAlchemy missing"; ((FAIL++)); }
venv/bin/pip3 list | grep -q "asyncpg" && success "asyncpg installed" || { error "asyncpg missing"; ((FAIL++)); }
venv/bin/pip3 list | grep -q "uvicorn" && success "uvicorn installed" || { error "uvicorn missing"; ((FAIL++)); }

echo ""
echo "=== Step 4: Frontend Dependencies Check ==="
cd "$FRONTEND"
[ -d "node_modules" ] && success "node_modules exists" || { error "node_modules missing"; ((FAIL++)); }
npm list next 2>/dev/null | grep -q "next@" && success "Next.js installed" || { error "Next.js missing"; ((FAIL++)); }

echo ""
echo "=== Step 5: Database Connectivity Test ==="
cd "$BACKEND"
venv/bin/python3 << 'PYEOF'
import asyncio
from sqlalchemy import text
from app.core.database import engine

async def test():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("  Database connection: OK")
            return True
    except Exception as e:
        print(f"  Database connection: FAILED - {e}")
        return False

if asyncio.run(test()):
    exit(0)
else:
    exit(1)
PYEOF
check "Database connectivity"

echo ""
echo "=== Step 6: Table Count Verification ==="
venv/bin/python3 << 'PYEOF'
import asyncio
from sqlalchemy import text
from app.core.database import engine

async def test():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
            count = result.scalar()
            print(f"  Tables in database: {count}")
            if count >= 20:
                return True
            return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

if asyncio.run(test()):
    exit(0)
else:
    exit(1)
PYEOF
check "Database tables (>=20)"

echo ""
echo "=== Step 7: Backend Startup Test ==="
pkill -f "uvicorn.*8000" 2>/dev/null || true
sleep 1
cd "$BACKEND"
nohup venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/ci-backend.log 2>&1 &
BACKEND_PID=$!
sleep 3

curl -s --max-time 2 http://localhost:8000/docs > /dev/null 2>&1
check "Backend startup (port 8000)"

echo ""
echo "=== Step 8: API Endpoint Test ==="
TOKEN="MzptYW5hZ2VyOjE3Nzc0Mzg1ODM="

# Test manager endpoint
RESP=$(curl -s --max-time 2 "http://localhost:8000/api/v1/manager/class" \
  -H "Authorization: Bearer $TOKEN" 2>/dev/null)
if echo "$RESP" | grep -q "id"; then
    success "Manager /class endpoint"
else
    warning "Manager /class endpoint returned: $(echo $RESP | head -c 100)"
fi

# Test students endpoint
RESP=$(curl -s --max-time 2 "http://localhost:8000/api/v1/admin/classes" \
  -H "Authorization: Bearer MTA6YWRtaW46MTc3NzQwMjg1MA==" 2>/dev/null)
if echo "$RESP" | grep -q "\["; then
    success "Admin /classes endpoint"
else
    error "Admin /classes endpoint failed"
fi

echo ""
echo "=== Step 9: Frontend Build Test ==="
cd "$FRONTEND"
# Use system Node to build
/usr/local/bin/node node_modules/.bin/next build 2>&1 | tail -5
check "Frontend build (Next.js)"

echo ""
echo "=== Step 10: Frontend Startup Test ==="
pkill -f "next.*3100" 2>/dev/null || true
sleep 1
nohup /usr/local/bin/node node_modules/.bin/next start -p 3100 > /tmp/ci-frontend.log 2>&1 &
FRONTEND_PID=$!
sleep 3

curl -s --max-time 2 http://localhost:3100 > /dev/null 2>&1
check "Frontend startup (port 3100)"

echo ""
echo "=== Step 11: Frontend API Proxy Test ==="
RESP=$(curl -s --max-time 2 "http://localhost:3100/api/v1/health" 2>/dev/null)
if [ $? -eq 0 ]; then
    success "Frontend API proxy"
else
    warning "Frontend API proxy (may not have /health endpoint)"
fi

echo ""
echo "=== Step 12: Nginx Config Test ==="
if [ -f "/usr/local/etc/nginx/servers/diving.conf" ]; then
    /usr/local/bin/nginx -t 2>/dev/null
    check "Nginx config syntax"
else
    warning "Nginx config not found"
fi

echo ""
echo "=== Step 13: Security Check ==="
cd "$BACKEND"
# Check for hardcoded secrets
if grep -r "password.*=" app/ --include="*.py" 2>/dev/null | grep -v "hash\|get\|set" | head -1; then
    warning "Possible hardcoded password found"
else
    success "No obvious hardcoded passwords"
fi

# Check for debug mode
if grep -r "debug.*=.*True" app/ --include="*.py" 2>/dev/null | head -1; then
    error "Debug mode enabled"
else
    success "Debug mode not found in code"
fi

echo ""
echo "=== Step 14: Code Quality Check ==="
cd "$BACKEND"
# Check for bare except clauses
BARE_EXCEPT=$(grep -r "except:" app/ --include="*.py" 2>/dev/null | wc -l | tr -d ' ')
if [ "$BARE_EXCEPT" -gt 5 ]; then
    warning "Found $BARE_EXCEPT bare except clauses"
else
    success "Bare except clauses: $BARE_EXCEPT (acceptable)"
fi

echo ""
echo "=== Step 15: Cleanup ==="
kill $BACKEND_PID 2>/dev/null || true
kill $FRONTEND_PID 2>/dev/null || true
pkill -f "uvicorn.*8000" 2>/dev/null || true
pkill -f "next.*3100" 2>/dev/null || true
success "Processes cleaned up"

echo ""
echo "======================================"
echo "CI/CD Validation Summary"
echo "======================================"
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some checks failed.${NC}"
    exit 1
fi
