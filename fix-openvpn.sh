#!/bin/bash
#
# Quick Fix for OpenVPN Configuration
# This script sets up the OpenVPN server configuration
#

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║         OpenVPN Configuration Fix                            ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Fixing OpenVPN configuration...${NC}"
echo ""

# 1. Copy server configuration
echo "1. Creating OpenVPN server configuration..."
cp openvpn-server.conf /srv/tbaps/vpn/config/server.conf
chmod 644 /srv/tbaps/vpn/config/server.conf
echo -e "${GREEN}✓${NC} Server configuration created"

# 2. Generate server certificate
echo ""
echo "2. Generating server certificate..."
cd /srv/tbaps/vpn/ca

if [ ! -f "server.key" ]; then
    openssl genrsa -out server.key 2048
    chmod 600 server.key
    echo -e "${GREEN}✓${NC} Server private key generated"
fi

if [ ! -f "server.crt" ]; then
    openssl req -new -key server.key -out server.csr \
        -subj "/C=US/ST=California/L=San Francisco/O=TBAPS/OU=IT/CN=tbaps-vpn-server"
    
    openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
        -CAcreateserial -out server.crt -days 3650 -sha256
    
    chmod 644 server.crt
    rm server.csr
    echo -e "${GREEN}✓${NC} Server certificate generated"
fi

# 3. Generate DH parameters (this may take a while)
echo ""
echo "3. Generating Diffie-Hellman parameters (this may take 1-2 minutes)..."
if [ ! -f "dh.pem" ]; then
    openssl dhparam -out dh.pem 2048
    chmod 644 dh.pem
    echo -e "${GREEN}✓${NC} DH parameters generated"
else
    echo -e "${GREEN}✓${NC} DH parameters already exist"
fi

# 4. Copy files to the correct location
echo ""
echo "4. Organizing certificate files..."
mkdir -p /srv/tbaps/vpn/certs/pki
cp ca.crt /srv/tbaps/vpn/certs/pki/
cp server.crt /srv/tbaps/vpn/certs/pki/
cp server.key /srv/tbaps/vpn/certs/pki/
cp dh.pem /srv/tbaps/vpn/certs/pki/
cp /srv/tbaps/vpn/ta.key /srv/tbaps/vpn/config/
echo -e "${GREEN}✓${NC} Files organized"

# 5. Restart OpenVPN
echo ""
echo "5. Restarting OpenVPN container..."
cd /home/kali/Desktop/MACHINE
docker-compose -f docker-compose.vpn.yml restart openvpn
echo -e "${GREEN}✓${NC} OpenVPN restarted"

# 6. Wait and check status
echo ""
echo "6. Checking OpenVPN status..."
sleep 5

if docker ps | grep tbaps-openvpn | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} OpenVPN is running!"
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║         OpenVPN Configuration Fixed Successfully!            ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "OpenVPN Server is now running on port 1194/UDP"
    echo ""
    echo "Next steps:"
    echo "  1. Generate VPN certificates:"
    echo "     cd vpn/scripts"
    echo "     ./generate-nef-certificate.sh \"Test User\" \"test@example.com\""
    echo ""
    echo "  2. Check OpenVPN logs:"
    echo "     docker logs tbaps-openvpn"
    echo ""
else
    echo -e "${RED}✗${NC} OpenVPN is not running. Check logs:"
    echo "     docker logs tbaps-openvpn"
fi

echo ""
