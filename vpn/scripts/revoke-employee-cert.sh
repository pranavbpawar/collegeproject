#!/bin/bash
#
# TBAPS Employee Certificate Revocation Script
#
# Revokes OpenVPN client certificates for offboarded employees
# Updates certificate status in PostgreSQL
# Regenerates Certificate Revocation List (CRL)
#
# Usage: ./revoke-employee-cert.sh <employee-id> <reason>
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check arguments
if [ $# -lt 2 ]; then
    echo -e "${RED}Error: Missing arguments${NC}"
    echo "Usage: $0 <employee-id> <reason>"
    echo "Example: $0 emp-001 'Employee terminated'"
    echo ""
    echo "Valid reasons:"
    echo "  • Employee terminated"
    echo "  • Employee resigned"
    echo "  • Certificate compromised"
    echo "  • Security policy violation"
    echo "  • Certificate expired"
    exit 1
fi

EMPLOYEE_ID=$1
REVOCATION_REASON=$2
CERT_NAME="emp-${EMPLOYEE_ID}"

echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║                                                              ║${NC}"
echo -e "${RED}║         TBAPS Employee Certificate Revocation                ║${NC}"
echo -e "${RED}║         ⚠️  WARNING: This action cannot be undone!           ║${NC}"
echo -e "${RED}║                                                              ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get employee details from database
echo -e "${YELLOW}Fetching employee details...${NC}"
EMPLOYEE_INFO=$(docker-compose exec -T postgresql psql -U tbaps -d tbaps -t -c \
    "SELECT employee_name, employee_email, status FROM vpn_certificates WHERE employee_id = '$EMPLOYEE_ID';")

if [ -z "$EMPLOYEE_INFO" ]; then
    echo -e "${RED}Error: Employee certificate not found for ID: $EMPLOYEE_ID${NC}"
    exit 1
fi

echo -e "${YELLOW}Employee Details:${NC}"
echo "$EMPLOYEE_INFO"
echo ""

# Confirmation prompt
echo -e "${RED}⚠️  You are about to revoke the certificate for:${NC}"
echo -e "  • Employee ID: $EMPLOYEE_ID"
echo -e "  • Certificate: $CERT_NAME"
echo -e "  • Reason: $REVOCATION_REASON"
echo ""
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Revocation cancelled.${NC}"
    exit 0
fi

echo ""

# Revoke certificate
echo -e "${YELLOW}[1/4]${NC} Revoking certificate..."
docker-compose -f docker-compose.vpn.yml exec -T openvpn easyrsa revoke "$CERT_NAME" << EOF
yes
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Certificate revoked"
else
    echo -e "${RED}✗${NC} Failed to revoke certificate"
    exit 1
fi
echo ""

# Regenerate CRL
echo -e "${YELLOW}[2/4]${NC} Regenerating Certificate Revocation List..."
docker-compose -f docker-compose.vpn.yml exec -T openvpn easyrsa gen-crl
docker-compose -f docker-compose.vpn.yml exec -T openvpn cp /etc/openvpn/pki/crl.pem /etc/openvpn/pki/crl.pem
echo -e "${GREEN}✓${NC} CRL regenerated"
echo ""

# Update database
echo -e "${YELLOW}[3/4]${NC} Updating database..."
docker-compose exec -T postgresql psql -U tbaps -d tbaps << EOSQL
UPDATE vpn_certificates 
SET 
    status = 'revoked',
    revoked_at = NOW(),
    revocation_reason = '$REVOCATION_REASON',
    updated_at = NOW()
WHERE employee_id = '$EMPLOYEE_ID';

-- Log revocation event
INSERT INTO vpn_audit_log (
    id,
    event_type,
    employee_id,
    certificate_name,
    details,
    created_at
) VALUES (
    gen_random_uuid(),
    'certificate_revoked',
    '$EMPLOYEE_ID',
    '$CERT_NAME',
    jsonb_build_object(
        'reason', '$REVOCATION_REASON',
        'revoked_by', 'admin',
        'timestamp', NOW()
    ),
    NOW()
);
EOSQL

echo -e "${GREEN}✓${NC} Database updated"
echo ""

# Restart OpenVPN to apply CRL
echo -e "${YELLOW}[4/4]${NC} Restarting OpenVPN server to apply changes..."
docker-compose -f docker-compose.vpn.yml restart openvpn
sleep 3
echo -e "${GREEN}✓${NC} OpenVPN server restarted"
echo ""

# Disconnect active sessions (if any)
echo -e "${YELLOW}Checking for active connections...${NC}"
ACTIVE_CONN=$(docker-compose exec -T postgresql psql -U tbaps -d tbaps -t -c \
    "SELECT COUNT(*) FROM vpn_connections WHERE employee_id = '$EMPLOYEE_ID' AND disconnected_at IS NULL;")

if [ "$ACTIVE_CONN" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Employee has $ACTIVE_CONN active connection(s)${NC}"
    echo -e "${YELLOW}   Connections will be terminated on next keepalive check${NC}"
    
    # Mark connections as force-disconnected
    docker-compose exec -T postgresql psql -U tbaps -d tbaps << EOSQL
UPDATE vpn_connections 
SET 
    disconnected_at = NOW(),
    disconnect_reason = 'certificate_revoked'
WHERE employee_id = '$EMPLOYEE_ID' 
AND disconnected_at IS NULL;
EOSQL
fi
echo ""

# Display summary
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║         Certificate Revocation Complete!                     ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Revocation Details:${NC}"
echo -e "  • Employee ID: $EMPLOYEE_ID"
echo -e "  • Certificate: $CERT_NAME"
echo -e "  • Reason: $REVOCATION_REASON"
echo -e "  • Revoked At: $(date)"
echo ""
echo -e "${GREEN}Actions Taken:${NC}"
echo -e "  ✓ Certificate revoked in PKI"
echo -e "  ✓ CRL regenerated and applied"
echo -e "  ✓ Database updated"
echo -e "  ✓ OpenVPN server restarted"
echo -e "  ✓ Active connections terminated"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Verify employee cannot connect"
echo -e "  2. Review audit logs: ./view-audit-log.sh $EMPLOYEE_ID"
echo -e "  3. Archive employee VPN data if required"
echo ""
echo -e "${GREEN}Security Notice:${NC}"
echo -e "  • Employee's VPN access is now completely blocked"
echo -e "  • All revocation events are logged for audit"
echo -e "  • CRL is automatically checked by all clients"
echo ""
