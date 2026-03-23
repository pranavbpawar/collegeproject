#!/bin/bash
#
# Simple OpenVPN Setup using kylemanna/openvpn
#

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Simple OpenVPN Setup                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

OVPN_DATA="ovpn-data"
SERVER_URL="udp://127.0.0.1"

echo -e "${YELLOW}Setting up OpenVPN with kylemanna/openvpn image...${NC}"
echo ""

# Step 1: Create volume
echo "1. Creating Docker volume for OpenVPN data..."
if docker volume ls | grep -q "$OVPN_DATA"; then
    echo -e "${GREEN}✓${NC} Volume already exists"
else
    docker volume create --name $OVPN_DATA
    echo -e "${GREEN}✓${NC} Volume created"
fi
echo ""

# Step 2: Initialize configuration
echo "2. Initializing OpenVPN configuration..."
docker run -v $OVPN_DATA:/etc/openvpn --rm kylemanna/openvpn ovpn_genconfig -u $SERVER_URL
echo -e "${GREEN}✓${NC} Configuration initialized"
echo ""

# Step 3: Generate CA and certificates (non-interactive)
echo "3. Generating CA and certificates..."
echo ""
echo -e "${YELLOW}Note: This will use default values for certificate fields${NC}"
docker run -v $OVPN_DATA:/etc/openvpn --rm -e EASYRSA_BATCH=1 kylemanna/openvpn ovpn_initpki nopass
echo -e "${GREEN}✓${NC} PKI initialized"
echo ""

# Step 4: Update docker-compose to use volume
echo "4. Updating docker-compose configuration..."
cat > docker-compose.vpn-simple.yml << 'EOF'
version: '3.8'

services:
  openvpn:
    image: kylemanna/openvpn:latest
    container_name: tbaps-openvpn
    ports:
      - "1194:1194/udp"
    cap_add:
      - NET_ADMIN
    volumes:
      - ovpn-data:/etc/openvpn
    restart: unless-stopped
    networks:
      - zt-network

networks:
  zt-network:
    name: zt-network

volumes:
  ovpn-data:
    external: true
EOF

echo -e "${GREEN}✓${NC} Docker compose file created: docker-compose.vpn-simple.yml"
echo ""

# Step 5: Start OpenVPN
echo "5. Starting OpenVPN..."
docker-compose -f docker-compose.vpn-simple.yml up -d
echo -e "${GREEN}✓${NC} OpenVPN started"
echo ""

# Step 6: Wait and verify
echo "6. Waiting for OpenVPN to start..."
sleep 5

if docker ps | grep tbaps-openvpn | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} OpenVPN is running!"
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         OpenVPN Setup Complete!                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "OpenVPN Server: udp://127.0.0.1:1194"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Generate a client certificate:"
    echo "   docker run -v ovpn-data:/etc/openvpn --rm -it kylemanna/openvpn easyrsa build-client-full CLIENTNAME nopass"
    echo ""
    echo "2. Export client configuration:"
    echo "   docker run -v ovpn-data:/etc/openvpn --rm kylemanna/openvpn ovpn_getclient CLIENTNAME > CLIENTNAME.ovpn"
    echo ""
    echo "3. View logs:"
    echo "   docker logs -f tbaps-openvpn"
    echo ""
else
    echo -e "${YELLOW}⚠${NC} OpenVPN may not be running. Check logs:"
    echo "   docker logs tbaps-openvpn"
fi
