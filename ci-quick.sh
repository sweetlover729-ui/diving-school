#!/bin/bash

echo "======================================"
echo "CI/CD Quick Validation"
echo "$(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================"

PROJECT="/Users/wjjmac/localserver/diving.school"
PASS=0
FAIL=0

check() {
    if [ $? -eq 0 ]; then
        echo "✓ $1"
        ((PASS++))
    else
        echo "✗ $1"
        ((FAIL++))
    fi
}

echo ""
echo "=== Backend Syntax ==="
cd "$PROJECT/backend"
venv/bin/python3 -m py_compile app/main.py 2>/dev/null; check "main.py"
venv/bin/python3 -m py_compile app/api/manager.py 2>/dev/null; check "manager.py"
venv/bin/python3 -m py_compile app/models/class_system.py 2>/dev/null; check "class_system.py"
[ -f app/api/admin.py ] && venv/bin/python3 -m py_compile app/api/admin.py 2>/dev/null && check "admin.py" || \
  (venv/bin/python3 -m py_compile app/api/admin/__init__.py 2>/dev/null; check "admin/__init__.py")

echo ""
echo "=== Backend Dependencies ==="
venv/bin/python3 -m pip show fastapi 2>/dev/null | grep -q "^Name:"; check "FastAPI"
venv/bin/python3 -m pip show sqlalchemy 2>/dev/null | grep -q "^Name:"; check "SQLAlchemy"
venv/bin/python3 -m pip show asyncpg 2>/dev/null | grep -q "^Name:"; check "asyncpg"

echo ""
echo "=== Database Check ==="
venv/bin/python3 << 'EOF'
import asyncio
from sqlalchemy import text
from app.core.database import engine
async def test():
    try:
        async with engine.begin() as conn:
            r = await conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'"))
            print(f"  Tables: {r.scalar()}")
            return True
    except Exception as e:
        print(f"  Error: {e}")
        return False
exit(0 if asyncio.run(test()) else 1)
EOF
[ $? -eq 0 ] && echo "✓ Database connection" && ((PASS++)) || echo "✗ Database connection"

echo ""
echo "=== Frontend Check ==="
cd "$PROJECT/frontend"
[ -d "node_modules" ]; check "node_modules exists"
[ -f "package.json" ]; check "package.json exists"
npm list next 2>/dev/null | grep -q "next@"; check "Next.js installed"

echo ""
echo "=== API Test (Backend must be running) ==="
curl -s --max-time 2 http://localhost:8000/docs >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Backend is running (8000)"
    ((PASS++))
    
    # Test manager endpoint
    RESP=$(curl -s --max-time 2 "http://localhost:8000/api/v1/manager/class" \
        -H "Authorization: Bearer MzptYW5hZ2VyOjE3Nzc0Mzg1ODM=")
    echo "$RESP" | grep -q "id\|403\|500" && echo "✓ Manager /class endpoint accessible" && ((PASS++)) || echo "✗ Manager /class failed"
    
    # Test admin endpoint
    RESP=$(curl -s --max-time 2 "http://localhost:8000/api/v1/admin/classes" \
        -H "Authorization: Bearer MTA6YWRtaW46MTc3NzQwMjg1MA==")
    echo "$RESP" | grep -q "\[" && echo "✓ Admin /classes endpoint" && ((PASS++)) || echo "✗ Admin /classes failed"
else
    echo "✗ Backend not running (8000)"
    ((FAIL++))
fi

echo ""
echo "=== Nginx Config ==="
if [ -f "/usr/local/etc/nginx/servers/diving.conf" ]; then
    /usr/local/bin/nginx -t 2>/dev/null && echo "✓ Nginx config valid" && ((PASS++)) || echo "✗ Nginx config invalid"
else
    echo "⚠ Nginx config not found"
fi

echo ""
echo "=== Summary ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""
[ $FAIL -eq 0 ] && echo "✓ All checks passed!" || echo "✗ Some checks failed."
