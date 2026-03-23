#!/bin/bash
#
# TBAPS NEF Certificate Generator
# Generates .nef VPN certificates for remote employees
#
# Usage: ./generate-nef-certificate.sh <employee_name> <employee_email>
# Example: ./generate-nef-certificate.sh "John Doe" "john.doe@company.com"
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check arguments
if [ -z "$1" ] || [ -z "$2" ]; then
    echo -e "${RED}Usage: $0 <employee_name> <employee_email>${NC}"
    echo "Example: $0 'John Doe' 'john.doe@company.com'"
    exit 1
fi

EMPLOYEE_NAME="$1"
EMPLOYEE_EMAIL="$2"
EMPLOYEE_ID=$(echo "$EMPLOYEE_NAME" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')

# Directories
VPN_DATA_DIR="/srv/tbaps/vpn/certificates"
CERT_DIR="/srv/tbaps/vpn/certs"
CONFIG_DIR="/srv/tbaps/vpn/configs"
CA_DIR="/srv/tbaps/vpn/ca"
LOG_FILE="/var/log/tbaps/nef_generation.log"

# Create directories
mkdir -p "$VPN_DATA_DIR" "$CERT_DIR" "$CONFIG_DIR" "$(dirname $LOG_FILE)"

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║         TBAPS NEF Certificate Generator                      ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Employee Details:${NC}"
echo "  • Name: $EMPLOYEE_NAME"
echo "  • Email: $EMPLOYEE_EMAIL"
echo "  • Certificate ID: $EMPLOYEE_ID"
echo ""

# Log start
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting certificate generation for $EMPLOYEE_NAME" >> "$LOG_FILE"

# Step 1: Generate private key and CSR
echo -e "${YELLOW}[1/8]${NC} Generating private key and certificate signing request..."
openssl req -new \
  -newkey rsa:2048 \
  -nodes \
  -out "$CERT_DIR/$EMPLOYEE_ID.csr" \
  -keyout "$CERT_DIR/$EMPLOYEE_ID.key" \
  -subj "/C=US/ST=State/L=City/O=TBAPS/CN=$EMPLOYEE_ID" \
  2>> "$LOG_FILE"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to generate certificate request${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Failed to generate CSR for $EMPLOYEE_NAME" >> "$LOG_FILE"
    exit 1
fi
echo -e "${GREEN}✓${NC} Private key and CSR generated"
echo ""

# Step 2: Sign the certificate (365 days validity)
echo -e "${YELLOW}[2/8]${NC} Signing certificate with CA..."
openssl x509 -req \
  -in "$CERT_DIR/$EMPLOYEE_ID.csr" \
  -CA "$CA_DIR/ca.crt" \
  -CAkey "$CA_DIR/ca.key" \
  -CAcreateserial \
  -out "$CERT_DIR/$EMPLOYEE_ID.crt" \
  -days 365 \
  -sha256 \
  2>> "$LOG_FILE"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to sign certificate${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Failed to sign certificate for $EMPLOYEE_NAME" >> "$LOG_FILE"
    exit 1
fi
echo -e "${GREEN}✓${NC} Certificate signed successfully"
echo ""

# Step 3: Get VPN server IP
echo -e "${YELLOW}[3/8]${NC} Reading VPN server configuration..."
VPN_SERVER_IP=$(cat /srv/tbaps/vpn/config/server_ip.txt 2>/dev/null || echo "192.168.1.100")
EXPIRY_DATE=$(date -d '+365 days' '+%Y-%m-%d')
GENERATED_DATE=$(date '+%Y-%m-%d')
echo -e "${GREEN}✓${NC} Server IP: $VPN_SERVER_IP"
echo ""

# Step 4: Create .nef configuration file
echo -e "${YELLOW}[4/8]${NC} Creating .nef configuration file..."
NEF_FILE="$CONFIG_DIR/$EMPLOYEE_ID.nef"

cat > "$NEF_FILE" << EOF
# TBAPS VPN Certificate (.nef format)
# Employee Name: $EMPLOYEE_NAME
# Employee Email: $EMPLOYEE_EMAIL
# Certificate ID: $EMPLOYEE_ID
# Generated Date: $GENERATED_DATE
# Certificate Expires: $EXPIRY_DATE
# Validity Period: 365 days

client
dev tun
proto udp
remote $VPN_SERVER_IP 1194

resolv-retry infinite
nobind
persist-key
persist-tun

user nobody
group nogroup

cipher AES-256-CBC
auth SHA256
tls-version-min 1.2

comp-lz4
verb 3
mute 20

# Embedded certificates below
EOF

echo -e "${GREEN}✓${NC} Configuration file created"
echo ""

# Step 5: Embed certificates into .nef file
echo -e "${YELLOW}[5/8]${NC} Embedding certificates and keys..."

echo "" >> "$NEF_FILE"
echo "<ca>" >> "$NEF_FILE"
cat "$CA_DIR/ca.crt" >> "$NEF_FILE"
echo "</ca>" >> "$NEF_FILE"

echo "" >> "$NEF_FILE"
echo "<cert>" >> "$NEF_FILE"
cat "$CERT_DIR/$EMPLOYEE_ID.crt" >> "$NEF_FILE"
echo "</cert>" >> "$NEF_FILE"

echo "" >> "$NEF_FILE"
echo "<key>" >> "$NEF_FILE"
cat "$CERT_DIR/$EMPLOYEE_ID.key" >> "$NEF_FILE"
echo "</key>" >> "$NEF_FILE"

echo "" >> "$NEF_FILE"
echo "<tls-auth>" >> "$NEF_FILE"
cat "/srv/tbaps/vpn/ta.key" >> "$NEF_FILE"
echo "</tls-auth>" >> "$NEF_FILE"
echo "key-direction 1" >> "$NEF_FILE"

echo -e "${GREEN}✓${NC} Certificates embedded"
echo ""

# Step 6: Set secure file permissions
echo -e "${YELLOW}[6/8]${NC} Setting secure file permissions..."
chmod 400 "$NEF_FILE"
chmod 400 "$CERT_DIR/$EMPLOYEE_ID.key"
chmod 400 "$CERT_DIR/$EMPLOYEE_ID.crt"
echo -e "${GREEN}✓${NC} Permissions set (read-only for owner)"
echo ""

# Step 7: Calculate checksums
echo -e "${YELLOW}[7/8]${NC} Calculating file checksum..."
FILE_CHECKSUM=$(sha256sum "$NEF_FILE" | awk '{print $1}')
FILE_SIZE=$(ls -lh "$NEF_FILE" | awk '{print $5}')
echo -e "${GREEN}✓${NC} Checksum: ${FILE_CHECKSUM:0:16}..."
echo ""

# Step 8: Log in database
echo -e "${YELLOW}[8/8]${NC} Recording certificate in database..."
docker-compose exec -T postgresql psql -U tbaps -d tbaps << SQLEOF
INSERT INTO vpn_certificates (
  id, 
  employee_name, 
  employee_email, 
  certificate_id,
  issued_at, 
  expires_at, 
  status, 
  config_file, 
  checksum,
  download_count
) VALUES (
  gen_random_uuid(),
  '$EMPLOYEE_NAME',
  '$EMPLOYEE_EMAIL',
  '$EMPLOYEE_ID',
  NOW(),
  NOW() + INTERVAL '365 days',
  'active',
  '$EMPLOYEE_ID.nef',
  '$FILE_CHECKSUM',
  0
) ON CONFLICT (certificate_id) 
DO UPDATE SET
  issued_at = EXCLUDED.issued_at,
  expires_at = EXCLUDED.expires_at,
  status = 'active',
  checksum = EXCLUDED.checksum,
  updated_at = NOW();
SQLEOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Database record created"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Certificate successfully created for $EMPLOYEE_NAME" >> "$LOG_FILE"
else
    echo -e "${YELLOW}⚠${NC}  Database logging failed (certificate still valid)"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database logging failed for $EMPLOYEE_NAME" >> "$LOG_FILE"
fi
echo ""

# Display summary
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║         NEF CERTIFICATE GENERATED SUCCESSFULLY!              ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Certificate Details:${NC}"
echo "  • Employee Name: $EMPLOYEE_NAME"
echo "  • Employee Email: $EMPLOYEE_EMAIL"
echo "  • Certificate ID: $EMPLOYEE_ID"
echo "  • File: $EMPLOYEE_ID.nef"
echo "  • Path: $NEF_FILE"
echo "  • Size: $FILE_SIZE"
echo "  • Checksum (SHA256): $FILE_CHECKSUM"
echo "  • Issued Date: $GENERATED_DATE"
echo "  • Expiry Date: $EXPIRY_DATE"
echo "  • Validity: 365 days"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Download $EMPLOYEE_ID.nef from $CONFIG_DIR/"
echo "  2. Send to employee via secure channel (encrypted email)"
echo "  3. Employee imports .nef into OpenVPN client"
echo "  4. Employee connects to VPN server at $VPN_SERVER_IP:1194"
echo "  5. Employee accesses TBAPS at https://tbaps.yourdomain.com"
echo ""
echo -e "${RED}Security Notice:${NC}"
echo "  • This file contains private keys - handle securely!"
echo "  • Use encrypted channels for distribution"
echo "  • Verify employee identity before sending"
echo "  • Delete file after employee confirms receipt"
echo ""
