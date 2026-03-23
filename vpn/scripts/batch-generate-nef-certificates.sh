#!/bin/bash
#
# TBAPS Batch NEF Certificate Generation
# Generate .nef certificates for multiple employees from CSV file
#
# Usage: ./batch-generate-nef-certificates.sh <csv_file>
# CSV Format: name,email,department,role
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default CSV file
CSV_FILE="${1:-employees.csv}"
LOG_FILE="/var/log/tbaps/batch_nef_generation_$(date +%Y%m%d_%H%M%S).log"
REPORT_FILE="/tmp/batch_nef_report_$(date +%Y%m%d_%H%M%S).txt"

# Check if CSV file exists
if [ ! -f "$CSV_FILE" ]; then
    echo -e "${RED}ERROR: CSV file not found: $CSV_FILE${NC}"
    echo ""
    echo "Usage: $0 <employees.csv>"
    echo ""
    echo "CSV Format (with header):"
    echo "name,email,department,role"
    echo ""
    echo "Example:"
    echo "name,email,department,role"
    echo "John Doe,john@company.com,Engineering,Senior Engineer"
    echo "Jane Smith,jane@company.com,Sales,Sales Manager"
    echo "Bob Johnson,bob@company.com,IT,System Administrator"
    exit 1
fi

# Create log directory
mkdir -p "$(dirname $LOG_FILE)"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║         TBAPS Batch NEF Certificate Generation               ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Log start
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting batch NEF generation from: $CSV_FILE" >> "$LOG_FILE"

# Count total employees
TOTAL_LINES=$(wc -l < "$CSV_FILE")
TOTAL_EMPLOYEES=$((TOTAL_LINES - 1))

if [ $TOTAL_EMPLOYEES -le 0 ]; then
    echo -e "${RED}ERROR: No employees found in CSV file${NC}"
    exit 1
fi

echo -e "${YELLOW}Processing $TOTAL_EMPLOYEES employees from $CSV_FILE${NC}"
echo ""

# Initialize counters
CURRENT=0
SUCCESS=0
FAILED=0
SKIPPED=0

# Arrays to track results
declare -a SUCCESS_LIST
declare -a FAILED_LIST
declare -a SKIPPED_LIST

# Process each line
while IFS=, read -r NAME EMAIL DEPARTMENT ROLE; do
    # Skip header
    if [ "$NAME" == "name" ]; then
        continue
    fi
    
    CURRENT=$((CURRENT + 1))
    
    # Validate required fields
    if [ -z "$NAME" ] || [ -z "$EMAIL" ]; then
        echo -e "${YELLOW}[$CURRENT/$TOTAL_EMPLOYEES]${NC} ${RED}SKIPPED${NC}: Invalid entry (missing name or email)"
        SKIPPED=$((SKIPPED + 1))
        SKIPPED_LIST+=("$NAME,$EMAIL,Missing required fields")
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] SKIPPED: $NAME - Missing required fields" >> "$LOG_FILE"
        continue
    fi
    
    # Validate email format
    if ! echo "$EMAIL" | grep -qE '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'; then
        echo -e "${YELLOW}[$CURRENT/$TOTAL_EMPLOYEES]${NC} ${RED}SKIPPED${NC}: Invalid email format for $NAME"
        SKIPPED=$((SKIPPED + 1))
        SKIPPED_LIST+=("$NAME,$EMAIL,Invalid email format")
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] SKIPPED: $NAME - Invalid email" >> "$LOG_FILE"
        continue
    fi
    
    echo -e "${YELLOW}[$CURRENT/$TOTAL_EMPLOYEES]${NC} Processing: $NAME ($EMAIL)"
    
    # Generate certificate
    bash "$(dirname "$0")/generate-nef-certificate.sh" "$NAME" "$EMAIL" >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        SUCCESS=$((SUCCESS + 1))
        SUCCESS_LIST+=("$NAME,$EMAIL,$DEPARTMENT,$ROLE")
        echo -e "${YELLOW}[$CURRENT/$TOTAL_EMPLOYEES]${NC} ${GREEN}SUCCESS${NC}: Certificate generated for $NAME"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $NAME" >> "$LOG_FILE"
    else
        FAILED=$((FAILED + 1))
        FAILED_LIST+=("$NAME,$EMAIL,Certificate generation failed")
        echo -e "${YELLOW}[$CURRENT/$TOTAL_EMPLOYEES]${NC} ${RED}FAILED${NC}: Certificate generation failed for $NAME"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAILED: $NAME" >> "$LOG_FILE"
    fi
    
    # Small delay to avoid overwhelming the system
    sleep 1
    
done < "$CSV_FILE"

# Calculate success rate
if [ $TOTAL_EMPLOYEES -gt 0 ]; then
    SUCCESS_RATE=$(( (SUCCESS * 100) / TOTAL_EMPLOYEES ))
else
    SUCCESS_RATE=0
fi

# Generate report
cat > "$REPORT_FILE" << EOF
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         BATCH NEF CERTIFICATE GENERATION REPORT              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

Generated: $(date '+%Y-%m-%d %H:%M:%S')
Source File: $CSV_FILE
Log File: $LOG_FILE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Employees: $TOTAL_EMPLOYEES
Successfully Generated: $SUCCESS
Failed: $FAILED
Skipped: $SKIPPED
Success Rate: $SUCCESS_RATE%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUCCESSFUL CERTIFICATES ($SUCCESS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

if [ ${#SUCCESS_LIST[@]} -gt 0 ]; then
    for entry in "${SUCCESS_LIST[@]}"; do
        echo "$entry" >> "$REPORT_FILE"
    done
else
    echo "None" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FAILED CERTIFICATES ($FAILED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

if [ ${#FAILED_LIST[@]} -gt 0 ]; then
    for entry in "${FAILED_LIST[@]}"; do
        echo "$entry" >> "$REPORT_FILE"
    done
else
    echo "None" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SKIPPED ENTRIES ($SKIPPED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

if [ ${#SKIPPED_LIST[@]} -gt 0 ]; then
    for entry in "${SKIPPED_LIST[@]}"; do
        echo "$entry" >> "$REPORT_FILE"
    done
else
    echo "None" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Review this report for any failures or skipped entries
2. Locate generated .nef files in: /srv/tbaps/vpn/configs/
3. Distribute certificates to employees via secure channel
4. Send setup instructions to each employee
5. Verify employees can connect to VPN
6. Monitor connection logs for successful connections

Certificate Location: /srv/tbaps/vpn/configs/
Log File: $LOG_FILE
Report File: $REPORT_FILE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

# Display summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║         BATCH GENERATION COMPLETED!                          ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Summary:${NC}"
echo "  • Total Employees: $TOTAL_EMPLOYEES"
echo "  • Successfully Generated: ${GREEN}$SUCCESS${NC}"
echo "  • Failed: ${RED}$FAILED${NC}"
echo "  • Skipped: ${YELLOW}$SKIPPED${NC}"
echo "  • Success Rate: $SUCCESS_RATE%"
echo ""
echo -e "${YELLOW}Files:${NC}"
echo "  • Certificates: /srv/tbaps/vpn/configs/"
echo "  • Log File: $LOG_FILE"
echo "  • Report File: $REPORT_FILE"
echo ""
echo -e "${BLUE}View full report:${NC}"
echo "  cat $REPORT_FILE"
echo ""

# Log completion
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Batch generation completed: $SUCCESS success, $FAILED failed, $SKIPPED skipped" >> "$LOG_FILE"

# Exit with appropriate code
if [ $FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi
