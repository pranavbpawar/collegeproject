#!/bin/bash
#
# TBAPS Employee Onboarding with NEF Certificate
# Interactive script to create new employee and generate .nef certificate
#
# Usage: ./onboard-employee-with-nef.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║         TBAPS Employee Onboarding System                     ║${NC}"
echo -e "${BLUE}║         with NEF VPN Certificate Generation                  ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Collect employee information
echo -e "${YELLOW}Please enter employee information:${NC}"
echo ""

read -p "Employee Full Name: " EMPLOYEE_NAME
read -p "Employee Email Address: " EMPLOYEE_EMAIL
read -p "Department: " DEPARTMENT
read -p "Job Role: " JOB_ROLE
read -p "Manager Name (optional): " MANAGER_NAME

# Validate required fields
if [ -z "$EMPLOYEE_NAME" ] || [ -z "$EMPLOYEE_EMAIL" ]; then
    echo -e "${RED}ERROR: Name and email are required${NC}"
    exit 1
fi

# Validate email format
if ! echo "$EMPLOYEE_EMAIL" | grep -qE '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'; then
    echo -e "${RED}ERROR: Invalid email format${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Review employee information:${NC}"
echo "  • Name: $EMPLOYEE_NAME"
echo "  • Email: $EMPLOYEE_EMAIL"
echo "  • Department: $DEPARTMENT"
echo "  • Role: $JOB_ROLE"
echo "  • Manager: ${MANAGER_NAME:-N/A}"
echo ""

read -p "Is this information correct? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Onboarding cancelled${NC}"
    exit 0
fi

echo ""

# Generate employee ID
EMPLOYEE_ID=$(uuidgen)
CERT_ID=$(echo "$EMPLOYEE_NAME" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')

# Step 1: Create employee in database
echo -e "${YELLOW}[1/4]${NC} Creating employee in TBAPS database..."
docker-compose exec -T postgresql psql -U tbaps -d tbaps << SQLEOF
INSERT INTO employees (
    id, 
    name, 
    email, 
    department, 
    role, 
    manager_name,
    status, 
    created_at
) VALUES (
    '$EMPLOYEE_ID', 
    '$EMPLOYEE_NAME', 
    '$EMPLOYEE_EMAIL', 
    '$DEPARTMENT', 
    '$JOB_ROLE',
    '$MANAGER_NAME', 
    'active', 
    NOW()
) ON CONFLICT (email) DO NOTHING;
SQLEOF

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to create employee in database${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Employee created with ID: $EMPLOYEE_ID"
echo ""

# Step 2: Generate .nef VPN certificate
echo -e "${YELLOW}[2/4]${NC} Generating .nef VPN certificate..."
bash "$(dirname "$0")/generate-nef-certificate.sh" "$EMPLOYEE_NAME" "$EMPLOYEE_EMAIL"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to generate .nef certificate${NC}"
    exit 1
fi
echo ""

# Step 3: Create welcome email
echo -e "${YELLOW}[3/4]${NC} Creating welcome email..."
VPN_SERVER_IP=$(cat /srv/tbaps/vpn/config/server_ip.txt 2>/dev/null || echo "192.168.1.100")
EXPIRY_DATE=$(date -d '+365 days' '+%Y-%m-%d')
WELCOME_EMAIL="/tmp/welcome_${CERT_ID}_$(date +%Y%m%d).txt"

cat > "$WELCOME_EMAIL" << EOF
Subject: Welcome to TBAPS - Your VPN Certificate is Ready

Dear $EMPLOYEE_NAME,

Welcome to the TBAPS system! We're excited to have you join our team.

Your VPN certificate has been generated and is ready for use. This will allow you 
to securely access TBAPS resources from anywhere.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VPN CONNECTION DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Certificate File: ${CERT_ID}.nef
VPN Server: $VPN_SERVER_IP:1194
Protocol: OpenVPN (UDP)
Encryption: AES-256-CBC
Authentication: SHA256
TLS Version: 1.2 and above
Certificate Issued: $(date '+%Y-%m-%d')
Certificate Expires: $EXPIRY_DATE
Validity Period: 365 days

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SETUP INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Download OpenVPN Client

Windows:
  • Visit: https://openvpn.net/client-connect-vpn/
  • Download and install OpenVPN Connect

macOS:
  • Download from App Store: "OpenVPN Connect"
  • Or use Homebrew: brew install --cask openvpn-connect

Linux (Ubuntu/Debian):
  • sudo apt-get update
  • sudo apt-get install openvpn

iOS:
  • Download "OpenVPN Connect" from App Store

Android:
  • Download "OpenVPN Connect" from Google Play Store

Step 2: Import Your Certificate

1. Locate your ${CERT_ID}.nef file (attached or provided separately)
2. Open OpenVPN client
3. Import the .nef file:
   - Windows/macOS: Drag and drop or File > Import
   - Linux: sudo openvpn --config ${CERT_ID}.nef
   - Mobile: Share file to OpenVPN app

Step 3: Connect to VPN

1. In OpenVPN client, select "${CERT_ID}"
2. Click "Connect" button
3. Wait for connection confirmation (usually 5-10 seconds)
4. You should see "Connected" status

Step 4: Access TBAPS

1. Open your web browser
2. Navigate to: https://tbaps.yourdomain.com
3. Login with your TBAPS credentials:
   - Email: $EMPLOYEE_EMAIL
   - Password: (will be provided separately)
4. You now have full access to TBAPS system

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECURITY NOTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  IMPORTANT SECURITY GUIDELINES:

• Keep your .nef certificate file confidential and secure
• NEVER share your certificate with anyone
• Do not email the certificate unencrypted
• Store the file in a secure location
• Use only on trusted devices
• Certificate is valid for 365 days
• Certificate will be automatically rotated before expiration
• Report any security concerns immediately to IT

🔒 Your certificate contains private cryptographic keys. Treat it like a password!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cannot connect to VPN:
  • Check your internet connection
  • Verify VPN server address: $VPN_SERVER_IP
  • Ensure port 1194/UDP is not blocked by firewall
  • Try from a different network

Certificate import fails:
  • Verify file is not corrupted (check file size > 0)
  • Ensure you're using OpenVPN client (not other VPN software)
  • Try re-downloading the certificate

Connected but cannot access TBAPS:
  • Verify you're connected to VPN (check OpenVPN status)
  • Clear browser cache and cookies
  • Try accessing: http://$VPN_SERVER_IP (should show VPN status)
  • Contact IT support if issue persists

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUPPORT CONTACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Email: vpn-support@company.com
Phone: +1-XXX-XXX-XXXX
Hours: Monday-Friday, 8 AM to 6 PM EST
Emergency: +1-XXX-XXX-9999 (24/7)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOUR EMPLOYEE INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Employee ID: $EMPLOYEE_ID
Name: $EMPLOYEE_NAME
Email: $EMPLOYEE_EMAIL
Department: $DEPARTMENT
Role: $JOB_ROLE
Manager: ${MANAGER_NAME:-N/A}
Onboarding Date: $(date '+%Y-%m-%d %H:%M:%S')

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Welcome aboard!

Best regards,
TBAPS Administration Team
EOF

echo -e "${GREEN}✓${NC} Welcome email created"
echo ""

# Step 4: Log onboarding event
echo -e "${YELLOW}[4/4]${NC} Logging onboarding event..."
docker-compose exec -T postgresql psql -U tbaps -d tbaps << SQLEOF
INSERT INTO vpn_audit_log (
    id,
    event_type,
    employee_id,
    certificate_name,
    details,
    severity,
    created_at
) VALUES (
    gen_random_uuid(),
    'employee_onboarded',
    '$EMPLOYEE_ID',
    '$CERT_ID',
    jsonb_build_object(
        'employee_name', '$EMPLOYEE_NAME',
        'employee_email', '$EMPLOYEE_EMAIL',
        'department', '$DEPARTMENT',
        'role', '$JOB_ROLE',
        'onboarding_date', NOW()
    ),
    'info',
    NOW()
);
SQLEOF

echo -e "${GREEN}✓${NC} Onboarding event logged"
echo ""

# Display summary
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║         EMPLOYEE ONBOARDING COMPLETED!                       ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Employee Information:${NC}"
echo "  • Name: $EMPLOYEE_NAME"
echo "  • Email: $EMPLOYEE_EMAIL"
echo "  • ID: $EMPLOYEE_ID"
echo "  • Department: $DEPARTMENT"
echo "  • Role: $JOB_ROLE"
echo "  • Manager: ${MANAGER_NAME:-N/A}"
echo ""
echo -e "${GREEN}VPN Certificate:${NC}"
echo "  • Certificate ID: $CERT_ID"
echo "  • File: ${CERT_ID}.nef"
echo "  • Location: /srv/tbaps/vpn/configs/${CERT_ID}.nef"
echo "  • Expiry: $EXPIRY_DATE"
echo ""
echo -e "${GREEN}Welcome Email:${NC}"
echo "  • File: $WELCOME_EMAIL"
echo "  • Recipient: $EMPLOYEE_EMAIL"
echo ""
echo -e "${YELLOW}Next Actions:${NC}"
echo "  1. Review welcome email: cat $WELCOME_EMAIL"
echo "  2. Send .nef file to employee via secure channel"
echo "  3. Send welcome email with instructions"
echo "  4. Set up TBAPS account credentials"
echo "  5. Confirm employee can connect to VPN"
echo "  6. Verify employee can access TBAPS system"
echo ""
echo -e "${BLUE}Certificate File Location:${NC}"
echo "  /srv/tbaps/vpn/configs/${CERT_ID}.nef"
echo ""
