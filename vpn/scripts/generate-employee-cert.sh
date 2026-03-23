#!/bin/bash
#
# TBAPS Employee Certificate Generation Script
#
# Generates OpenVPN client certificates for employees
# Stores certificate metadata in PostgreSQL
# Creates .ovpn configuration file
#
# Usage: ./generate-employee-cert.sh <employee-id> <employee-name> <employee-email>
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check arguments
if [ $# -lt 3 ]; then
    echo -e "${RED}Error: Missing arguments${NC}"
    echo "Usage: $0 <employee-id> <employee-name> <employee-email>"
    echo "Example: $0 emp-001 'John Doe' john.doe@company.com"
    exit 1
fi

EMPLOYEE_ID=$1
EMPLOYEE_NAME=$2
EMPLOYEE_EMAIL=$3
CERT_NAME="emp-${EMPLOYEE_ID}"
SERVER_IP="${OPENVPN_SERVER_IP:-YOUR_SERVER_IP}"
OUTPUT_DIR="./vpn/client-configs"

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║         TBAPS Employee Certificate Generation                ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Employee Details:${NC}"
echo -e "  • ID: $EMPLOYEE_ID"
echo -e "  • Name: $EMPLOYEE_NAME"
echo -e "  • Email: $EMPLOYEE_EMAIL"
echo -e "  • Certificate: $CERT_NAME"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Generate client certificate
echo -e "${YELLOW}[1/5]${NC} Generating client certificate..."
docker-compose -f docker-compose.vpn.yml exec -T openvpn easyrsa build-client-full "$CERT_NAME" nopass
echo -e "${GREEN}✓${NC} Certificate generated"
echo ""

# Extract certificates and keys
echo -e "${YELLOW}[2/5]${NC} Extracting certificates..."
docker-compose -f docker-compose.vpn.yml exec -T openvpn cat /etc/openvpn/pki/ca.crt > "$OUTPUT_DIR/${CERT_NAME}-ca.crt"
docker-compose -f docker-compose.vpn.yml exec -T openvpn cat "/etc/openvpn/pki/issued/${CERT_NAME}.crt" > "$OUTPUT_DIR/${CERT_NAME}.crt"
docker-compose -f docker-compose.vpn.yml exec -T openvpn cat "/etc/openvpn/pki/private/${CERT_NAME}.key" > "$OUTPUT_DIR/${CERT_NAME}.key"
docker-compose -f docker-compose.vpn.yml exec -T openvpn cat /etc/openvpn/pki/ta.key > "$OUTPUT_DIR/${CERT_NAME}-ta.key"
echo -e "${GREEN}✓${NC} Certificates extracted"
echo ""

# Create .ovpn configuration file
echo -e "${YELLOW}[3/5]${NC} Creating .ovpn configuration file..."
cat > "$OUTPUT_DIR/${CERT_NAME}.ovpn" << EOF
##############################################
# TBAPS OpenVPN Client Configuration
# 
# Employee: $EMPLOYEE_NAME
# Email: $EMPLOYEE_EMAIL
# Certificate: $CERT_NAME
# Generated: $(date)
##############################################

client
dev tun
proto udp

# Server address
remote $SERVER_IP 1194

# Connection settings
resolv-retry infinite
nobind
persist-key
persist-tun

# Security
remote-cert-tls server
cipher AES-256-CBC
auth SHA256
tls-version-min 1.2

# Compression
comp-lzo

# Logging
verb 3
mute 20

# User/Group (Unix/Linux only)
user nobody
group nogroup

# Embedded certificates and keys
<ca>
$(cat "$OUTPUT_DIR/${CERT_NAME}-ca.crt")
</ca>

<cert>
$(cat "$OUTPUT_DIR/${CERT_NAME}.crt")
</cert>

<key>
$(cat "$OUTPUT_DIR/${CERT_NAME}.key")
</key>

<tls-auth>
$(cat "$OUTPUT_DIR/${CERT_NAME}-ta.key")
</tls-auth>
key-direction 1
EOF

echo -e "${GREEN}✓${NC} .ovpn file created"
echo ""

# Store certificate metadata in database
echo -e "${YELLOW}[4/5]${NC} Storing certificate metadata in database..."
docker-compose exec -T postgresql psql -U tbaps -d tbaps << EOSQL
INSERT INTO vpn_certificates (
    id,
    employee_id,
    certificate_name,
    employee_name,
    employee_email,
    issued_at,
    expires_at,
    status,
    created_at
) VALUES (
    gen_random_uuid(),
    '$EMPLOYEE_ID',
    '$CERT_NAME',
    '$EMPLOYEE_NAME',
    '$EMPLOYEE_EMAIL',
    NOW(),
    NOW() + INTERVAL '365 days',
    'active',
    NOW()
) ON CONFLICT (employee_id) 
DO UPDATE SET
    certificate_name = EXCLUDED.certificate_name,
    issued_at = EXCLUDED.issued_at,
    expires_at = EXCLUDED.expires_at,
    status = 'active',
    updated_at = NOW();
EOSQL

echo -e "${GREEN}✓${NC} Metadata stored in database"
echo ""

# Clean up individual certificate files (keep only .ovpn)
echo -e "${YELLOW}[5/5]${NC} Cleaning up temporary files..."
rm -f "$OUTPUT_DIR/${CERT_NAME}-ca.crt"
rm -f "$OUTPUT_DIR/${CERT_NAME}.crt"
rm -f "$OUTPUT_DIR/${CERT_NAME}.key"
rm -f "$OUTPUT_DIR/${CERT_NAME}-ta.key"
echo -e "${GREEN}✓${NC} Cleanup complete"
echo ""

# Set proper permissions
chmod 600 "$OUTPUT_DIR/${CERT_NAME}.ovpn"

# Display summary
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║         Certificate Generation Complete!                     ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Certificate Details:${NC}"
echo -e "  • Employee: $EMPLOYEE_NAME ($EMPLOYEE_EMAIL)"
echo -e "  • Certificate: $CERT_NAME"
echo -e "  • Valid: 365 days"
echo -e "  • Encryption: AES-256-CBC"
echo -e "  • Authentication: SHA256"
echo ""
echo -e "${GREEN}Configuration File:${NC}"
echo -e "  • Location: $OUTPUT_DIR/${CERT_NAME}.ovpn"
echo -e "  • Size: $(du -h "$OUTPUT_DIR/${CERT_NAME}.ovpn" | cut -f1)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Securely send .ovpn file to employee"
echo -e "  2. Provide setup instructions (see setup-instructions.md)"
echo -e "  3. Employee imports .ovpn into OpenVPN client"
echo ""
echo -e "${RED}Security Notice:${NC}"
echo -e "  • This file contains private keys - handle securely!"
echo -e "  • Use encrypted channels for distribution"
echo -e "  • Delete file after employee confirms receipt"
echo ""
