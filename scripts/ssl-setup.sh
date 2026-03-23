#!/usr/bin/env bash
# ==============================================================================
# TBAPS SSL Setup — Let's Encrypt via Certbot
# Run after Nginx is installed and DNS is pointed to this server.
# Usage: sudo bash scripts/ssl-setup.sh <your-domain>
# Example: sudo bash scripts/ssl-setup.sh tbaps.yourcompany.local
# ==============================================================================

set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-admin@yourcompany.local}"

[[ -z "$DOMAIN" ]] && { echo "Usage: $0 <domain> [email]"; exit 1; }
[[ $EUID -ne 0 ]]  && { echo "Run as root: sudo $0 $DOMAIN"; exit 1; }

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

# ── Install certbot ────────────────────────────────────────────────────────────
if ! command -v certbot &>/dev/null; then
    info "Installing certbot..."
    apt-get update -q
    apt-get install -y certbot python3-certbot-nginx
fi

# ── Create ACME challenge directory ───────────────────────────────────────────
mkdir -p /var/www/certbot

# ── Update Nginx config with actual domain ─────────────────────────────────────
NGINX_CONF="/etc/nginx/sites-available/tbaps.conf"
if [[ -f "$NGINX_CONF" ]]; then
    sed -i "s/tbaps\.yourcompany\.local/$DOMAIN/g" "$NGINX_CONF"
    nginx -t && systemctl reload nginx
    info "Nginx config updated for domain: $DOMAIN"
fi

# ── Obtain certificate ─────────────────────────────────────────────────────────
info "Obtaining Let's Encrypt certificate for $DOMAIN ..."
certbot certonly \
    --nginx \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    --domains "$DOMAIN" \
    --redirect

# ── Set up auto-renewal ────────────────────────────────────────────────────────
info "Setting up auto-renewal cron job..."
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -

# ── Final reload ───────────────────────────────────────────────────────────────
nginx -t && systemctl reload nginx

info "SSL setup complete!"
info "Certificate: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
info "Auto-renewal: daily at 03:00 via cron"
echo ""
warn "For INTERNAL / self-signed certs (no public DNS), use:"
warn "  openssl req -x509 -nodes -days 365 -newkey rsa:4096 \\"
warn "    -keyout /etc/ssl/private/tbaps.key \\"
warn "    -out /etc/ssl/certs/tbaps.crt \\"
warn "    -subj '/CN=$DOMAIN'"
warn "Then update ssl_certificate paths in /etc/nginx/sites-available/tbaps.conf"
