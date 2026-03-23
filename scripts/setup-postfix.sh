#!/bin/bash
# ==============================================================================
# TBAPS — Self-Hosted Email Setup Script (Postfix + OpenDKIM)
# 
# WARNING: Run this on your production Linux server, NOT your home Windows/WSL
# machine! Port 25 is almost always blocked on home internet connections.
# ==============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root (use sudo)"
  exit 1
fi

echo "================================================================"
echo "          TBAPS Self-Hosted Email Setup (Postfix)               "
echo "================================================================"

read -p "Enter your application domain name (e.g., tbaps.yourdomain.com): " APP_DOMAIN
if [ -z "$APP_DOMAIN" ]; then
    echo "❌ Domain name cannot be empty."
    exit 1
fi

echo ""
echo "📦 1. Installing Postfix and OpenDKIM..."
# Pre-seed debconf so postfix doesn't prompt for configuration type interactively
echo "postfix postfix/main_mailer_type select Internet Site" | debconf-set-selections
echo "postfix postfix/mailname string $APP_DOMAIN" | debconf-set-selections

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y postfix mailutils opendkim opendkim-tools

echo ""
echo "⚙️ 2. Configuring Postfix..."

# Backup original config
cp /etc/postfix/main.cf /etc/postfix/main.cf.bak

# Configure main.cf
cat > /etc/postfix/main.cf <<EOF
# See /usr/share/postfix/main.cf.dist for a commented, more complete version
smtpd_banner = \$myhostname ESMTP \$mail_name (Ubuntu)
biff = no
append_dot_mydomain = no
readme_directory = no

# TLS parameters
smtpd_tls_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
smtpd_tls_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
smtpd_tls_security_level=may
smtp_tls_security_level=may

# Basic Settings
myhostname = $APP_DOMAIN
alias_maps = hash:/etc/aliases
alias_database = hash:/etc/aliases
myorigin = /etc/mailname
mydestination = \$myhostname, localhost.\$mydomain, localhost
relayhost = 

# SECURITY: Only allow sending from localhost!
# Prevents your server from becoming an open relay for spammers.
mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128
mailbox_size_limit = 0
recipient_delimiter = +
inet_interfaces = loopback-only
inet_protocols = all

# OpenDKIM Integration
milter_protocol = 6
milter_default_action = accept
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891
EOF

echo $APP_DOMAIN > /etc/mailname

echo ""
echo "🔑 3. Generating DKIM Keys..."

mkdir -p /etc/opendkim/keys/$APP_DOMAIN
chown -R opendkim:opendkim /etc/opendkim
chmod 700 /etc/opendkim/keys/$APP_DOMAIN

opendkim-genkey -b 2048 -d $APP_DOMAIN -D /etc/opendkim/keys/$APP_DOMAIN -s default -v
chown opendkim:opendkim /etc/opendkim/keys/$APP_DOMAIN/default.private
chmod 600 /etc/opendkim/keys/$APP_DOMAIN/default.private

# Configure OpenDKIM
cat > /etc/opendkim.conf <<EOF
Syslog                  yes
UMask                   002
Socket                  inet:8891@localhost
PidFile                 /run/opendkim/opendkim.pid
OversignHeaders         From
TrustAnchorFile         /usr/share/dns/root.key
UserID                  opendkim
KeyTable                refile:/etc/opendkim/KeyTable
SigningTable            refile:/etc/opendkim/SigningTable
ExternalIgnoreList      refile:/etc/opendkim/TrustedHosts
InternalHosts           refile:/etc/opendkim/TrustedHosts
EOF

# Setup OpenDKIM Maps
cat > /etc/opendkim/KeyTable <<EOF
default._domainkey.$APP_DOMAIN $APP_DOMAIN:default:/etc/opendkim/keys/$APP_DOMAIN/default.private
EOF

cat > /etc/opendkim/SigningTable <<EOF
*@$APP_DOMAIN default._domainkey.$APP_DOMAIN
EOF

cat > /etc/opendkim/TrustedHosts <<EOF
127.0.0.1
localhost
$APP_DOMAIN
EOF

chown -R opendkim:opendkim /etc/opendkim

# Restart services
echo ""
echo "🔄 4. Restarting Services..."
systemctl restart opendkim
systemctl restart postfix
systemctl enable opendkim
systemctl enable postfix

echo "================================================================"
echo "✅ Setup Complete!"
echo "Postfix is now listening on 127.0.0.1:25"
echo ""
echo "⚠️ CRITICAL NEXT STEP:"
echo "You MUST add the following DKIM TXT record to your DNS settings."
echo "If you skip this, all your emails will go to Spam."
echo ""
echo "Host/Name: default._domainkey"
echo "Value:"
cat /etc/opendkim/keys/$APP_DOMAIN/default.txt | grep -v '^-' | tr -d '\n' | tr -d '"' | sed 's/  */ /g'
echo ""
echo ""
echo "See docs/EMAIL_DNS_RECORDS.md for the SPF and DMARC records."
echo "================================================================"
