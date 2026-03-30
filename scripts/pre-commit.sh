#!/bin/bash
# Pre-commit hook for ClinicOS
# Runs backend and frontend tests before allowing commit

set -e

echo "🧪 Running ClinicOS pre-commit tests..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend tests should run (if backend files changed)
BACKEND_CHANGED=$(git diff --cached --name-only | grep -E '^backend/' || true)

# Check if frontend tests should run (if frontend files changed)
FRONTEND_CHANGED=$(git diff --cached --name-only | grep -E '^frontend/' || true)

# If no relevant files changed, skip tests
if [ -z "$BACKEND_CHANGED" ] && [ -z "$FRONTEND_CHANGED" ]; then
    echo -e "${YELLOW}⏭️  No backend or frontend files changed, skipping tests${NC}"
    exit 0
fi

# Run backend tests if backend files changed
if [ -n "$BACKEND_CHANGED" ]; then
    echo -e "${YELLOW}🔧 Running backend tests...${NC}"
    cd backend
    if python -m pytest tests/ -x -q --tb=short; then
        echo -e "${GREEN}✅ Backend tests passed${NC}"
    else
        echo -e "${RED}❌ Backend tests failed${NC}"
        echo -e "${RED}Fix tests before committing${NC}"
        exit 1
    fi
    cd ..
    echo ""
fi

# Run frontend tests if frontend files changed
if [ -n "$FRONTEND_CHANGED" ]; then
    echo -e "${YELLOW}🎭 Running Playwright E2E tests...${NC}"
    
    # Check if backend is running
    if ! curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo -e "${RED}❌ Backend not running on localhost:8000${NC}"
        echo -e "${YELLOW}Start backend: cd backend && uvicorn app.main:app --reload --port 8000${NC}"
        exit 1
    fi
    
    if npx playwright test; then
        echo -e "${GREEN}✅ Frontend E2E tests passed${NC}"
    else
        echo -e "${RED}❌ Frontend E2E tests failed${NC}"
        echo -e "${RED}Fix tests before committing${NC}"
        exit 1
    fi
    echo ""
fi

echo -e "${GREEN}✅ All tests passed - ready to commit!${NC}"
exit 0
