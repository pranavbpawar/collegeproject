#!/bin/bash
#
# TBAPS OpenVPN Server Setup Script
# 
# Initializes OpenVPN server with:
# - Certificate Authority (CA)
# - Server certificates
# - Diffie-Hellman parameters
# - TLS authentication key
# - Server configuration
#
# Usage: ./openvpn-setup.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
OPENVPN_DIR="./vpn"
CONFIG_DIR="$OPENVPN_DIR/config"
CERTS_DIR="$OPENVPN_DIR/certs"
LOGS_DIR="$OPENVPN_DIR/logs"
SERVER_IP="${OPENVPN_SERVER_IP:-YOUR_SERVER_IP}"

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║         TBAPS OpenVPN Server Setup                           ║${NC}"
echo -e "${GREEN}║         Self-Hosted VPN Infrastructure                       ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create directory structure
echo -e "${YELLOW}[1/8]${NC} Creating directory structure..."
mkdir -p "$CONFIG_DIR" "$CERTS_DIR" "$LOGS_DIR"
echo -e "${GREEN}✓${NC} Directories created"
echo ""

# Start OpenVPN container
echo -e "${YELLOW}[2/8]${NC} Starting OpenVPN container..."
docker-compose -f docker-compose.vpn.yml up -d openvpn
sleep 5
echo -e "${GREEN}✓${NC} OpenVPN container started"
echo ""

# Initialize PKI (Public Key Infrastructure)
echo -e "${YELLOW}[3/8]${NC} Initializing PKI..."
docker-compose -f docker-compose.vpn.yml exec -T openvpn ovpn_genconfig -u udp://$SERVER_IP
docker-compose -f docker-compose.vpn.yml exec -T openvpn ovpn_initpki nopass
echo -e "${GREEN}✓${NC} PKI initialized"
echo ""

# Generate Diffie-Hellman parameters (this takes a while)
echo -e "${YELLOW}[4/8]${NC} Generating Diffie-Hellman parameters (this may take 5-10 minutes)..."
docker-compose -f docker-compose.vpn.yml exec -T openvpn bash -c \
  "openssl dhparam -out /etc/openvpn/pki/dh.pem 2048"
echo -e "${GREEN}✓${NC} DH parameters generated"
echo ""

# Generate TLS authentication key
echo -e "${YELLOW}[5/8]${NC} Generating TLS authentication key..."
docker-compose -f docker-compose.vpn.yml exec -T openvpn bash -c \
  "openvpn --genkey --secret /etc/openvpn/pki/ta.key"
echo -e "${GREEN}✓${NC} TLS auth key generated"
echo ""

# Create server configuration
echo -e "${YELLOW}[6/8]${NC} Creating server configuration..."
cat > "$CONFIG_DIR/server.conf" << 'EOF'
# TBAPS OpenVPN Server Configuration
# Generated: $(date)

# Network settings
port 1194
proto udp
dev tun

# SSL/TLS settings
ca /etc/openvpn/pki/ca.crt
cert /etc/openvpn/pki/issued/server.crt
key /etc/openvpn/pki/private/server.key
dh /etc/openvpn/pki/dh.pem
tls-auth /etc/openvpn/pki/ta.key 0

# Encryption settings
cipher AES-256-CBC
auth SHA256
tls-version-min 1.2

# Network configuration
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist /etc/openvpn/ipp.txt

# Push routes to clients
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"
push "dhcp-option DNS 8.8.4.4"

# Client settings
client-to-client
keepalive 10 120
max-clients 500

# Privileges
user nobody
group nogroup
persist-key
persist-tun

# Logging
status /var/log/openvpn/openvpn-status.log
log-append /var/log/openvpn/openvpn.log
verb 3
mute 20

# Performance
comp-lzo
push "comp-lzo"

# Security
duplicate-cn
crl-verify /etc/openvpn/pki/crl.pem

# Management interface for monitoring
management localhost 7505
EOF

echo -e "${GREEN}✓${NC} Server configuration created"
echo ""

# Create Certificate Revocation List (CRL)
echo -e "${YELLOW}[7/8]${NC} Creating Certificate Revocation List..."
docker-compose -f docker-compose.vpn.yml exec -T openvpn bash -c \
  "easyrsa gen-crl && cp /etc/openvpn/pki/crl.pem /etc/openvpn/pki/crl.pem"
echo -e "${GREEN}✓${NC} CRL created"
echo ""

# Set proper permissions
echo -e "${YELLOW}[8/8]${NC} Setting permissions..."
chmod 700 "$CERTS_DIR"
chmod 600 "$CONFIG_DIR/server.conf"
echo -e "${GREEN}✓${NC} Permissions set"
echo ""

# Restart OpenVPN with new configuration
echo -e "${YELLOW}Restarting OpenVPN server...${NC}"
docker-compose -f docker-compose.vpn.yml restart openvpn
sleep 3
echo -e "${GREEN}✓${NC} OpenVPN server restarted"
echo ""

# Display summary
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║         OpenVPN Server Setup Complete!                       ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Server Details:${NC}"
echo -e "  • Server IP: $SERVER_IP"
echo -e "  • Port: 1194/UDP"
echo -e "  • Encryption: AES-256-CBC"
echo -e "  • Authentication: SHA256"
echo -e "  • TLS Version: 1.2+"
echo -e "  • Max Clients: 500"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo -e "  1. Generate employee certificates: ./generate-employee-cert.sh <employee-id>"
echo -e "  2. Configure firewall: sudo ufw allow 1194/udp"
echo -e "  3. Monitor logs: docker-compose -f docker-compose.vpn.yml logs -f openvpn"
echo ""
echo -e "${YELLOW}Important Files:${NC}"
echo -e "  • CA Certificate: $CERTS_DIR/ca.crt"
echo -e "  • Server Config: $CONFIG_DIR/server.conf"
echo -e "  • Logs: $LOGS_DIR/"
echo ""
