#!/bin/bash
#
# OpenVPN Diagnostics
#

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         OpenVPN Diagnostics                                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "=== Container Status ==="
docker ps -a | grep openvpn
echo ""

echo "=== Container Logs (last 50 lines) ==="
docker logs tbaps-openvpn 2>&1 | tail -50
echo ""

echo "=== Configuration Files ==="
echo "Server config:"
ls -lh /srv/tbaps/vpn/config/server.conf 2>/dev/null || echo "  ✗ Not found"
echo ""

echo "Certificates:"
ls -lh /srv/tbaps/vpn/certs/pki/ 2>/dev/null || echo "  ✗ Directory not found"
echo ""

echo "=== Volume Mounts ==="
docker inspect tbaps-openvpn | grep -A 10 "Mounts"
echo ""
