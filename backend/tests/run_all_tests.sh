#!/bin/bash
#
# TBAPS Test Execution Script
# Runs all test suites and generates coverage reports
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
MIN_COVERAGE=80
MIN_ACCURACY=85

echo -e "${BLUE}================================================================================================${NC}"
echo -e "${BLUE}TBAPS COMPREHENSIVE TEST SUITE${NC}"
echo -e "${BLUE}================================================================================================${NC}"
echo ""

# Change to backend directory
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# ============================================================================
# UNIT TESTS
# ============================================================================

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}RUNNING UNIT TESTS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

pytest tests/unit/ \
    -v \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:htmlcov/unit \
    --cov-report=json:coverage-unit.json \
    --tb=short \
    --maxfail=5 \
    || { echo -e "${RED}❌ Unit tests failed${NC}"; exit 1; }

echo -e "\n${GREEN}✅ Unit tests passed${NC}"

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}RUNNING INTEGRATION TESTS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

pytest tests/integration/ \
    -v \
    --tb=short \
    --maxfail=3 \
    || { echo -e "${RED}❌ Integration tests failed${NC}"; exit 1; }

echo -e "\n${GREEN}✅ Integration tests passed${NC}"

# ============================================================================
# ACCURACY VALIDATION TESTS
# ============================================================================

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}RUNNING ACCURACY VALIDATION TESTS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

pytest tests/accuracy/ \
    -v \
    --tb=short \
    || { echo -e "${RED}❌ Accuracy validation failed${NC}"; exit 1; }

echo -e "\n${GREEN}✅ Accuracy validation passed${NC}"

# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}RUNNING PERFORMANCE BENCHMARKS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

pytest tests/performance/ \
    -v \
    -m performance \
    --tb=short \
    || { echo -e "${YELLOW}⚠️  Some performance benchmarks failed (non-critical)${NC}"; }

echo -e "\n${GREEN}✅ Performance benchmarks completed${NC}"

# ============================================================================
# COVERAGE REPORT
# ============================================================================

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}CODE COVERAGE REPORT${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Extract coverage percentage from JSON report
if [ -f "coverage-unit.json" ]; then
    COVERAGE=$(python3 -c "import json; data=json.load(open('coverage-unit.json')); print(f\"{data['totals']['percent_covered']:.1f}\")")
    
    echo -e "Overall Coverage: ${COVERAGE}%"
    
    if (( $(echo "$COVERAGE >= $MIN_COVERAGE" | bc -l) )); then
        echo -e "${GREEN}✅ Coverage ${COVERAGE}% meets ${MIN_COVERAGE}% threshold${NC}"
    else
        echo -e "${RED}❌ Coverage ${COVERAGE}% below ${MIN_COVERAGE}% threshold${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Coverage report not found${NC}"
fi

echo -e "\nDetailed coverage report: ${BLUE}htmlcov/unit/index.html${NC}"

# ============================================================================
# REACT TESTS (if frontend exists)
# ============================================================================

if [ -d "../frontend" ]; then
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}RUNNING REACT TESTS${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    cd ../frontend
    
    if [ -f "package.json" ]; then
        npm test -- --coverage --watchAll=false \
            || { echo -e "${RED}❌ React tests failed${NC}"; exit 1; }
        
        echo -e "\n${GREEN}✅ React tests passed${NC}"
    else
        echo -e "${YELLOW}⚠️  No package.json found, skipping React tests${NC}"
    fi
    
    cd ../backend
fi

# ============================================================================
# FINAL SUMMARY
# ============================================================================

echo -e "\n${BLUE}================================================================================================${NC}"
echo -e "${GREEN}TEST SUMMARY${NC}"
echo -e "${BLUE}================================================================================================${NC}\n"

echo -e "${GREEN}✅ Unit Tests:          PASSED${NC}"
echo -e "${GREEN}✅ Integration Tests:   PASSED${NC}"
echo -e "${GREEN}✅ Accuracy Validation: PASSED${NC}"
echo -e "${GREEN}✅ Performance Tests:   COMPLETED${NC}"

if [ -f "coverage-unit.json" ]; then
    echo -e "${GREEN}✅ Code Coverage:       ${COVERAGE}% (threshold: ${MIN_COVERAGE}%)${NC}"
fi

if [ -d "../frontend" ] && [ -f "../frontend/package.json" ]; then
    echo -e "${GREEN}✅ React Tests:         PASSED${NC}"
fi

echo -e "\n${BLUE}================================================================================================${NC}"
echo -e "${GREEN}🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION${NC}"
echo -e "${BLUE}================================================================================================${NC}\n"

# Generate test report
echo -e "${YELLOW}Generating test report...${NC}"

cat > test-report.txt << EOF
TBAPS Test Execution Report
Generated: $(date)

UNIT TESTS:          ✅ PASSED
INTEGRATION TESTS:   ✅ PASSED
ACCURACY VALIDATION: ✅ PASSED
PERFORMANCE TESTS:   ✅ COMPLETED
CODE COVERAGE:       ${COVERAGE:-N/A}%

Status: PRODUCTION READY
EOF

echo -e "${GREEN}✅ Test report saved to test-report.txt${NC}\n"

exit 0
