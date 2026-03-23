# TBAPS VPN - Employee Setup Instructions

## 📋 Overview

Welcome to the TBAPS VPN! This guide will help you set up secure access to company resources.

**What is VPN?**
A Virtual Private Network (VPN) creates a secure, encrypted connection between your device and the company network, allowing you to access internal resources safely from anywhere.

---

## 🔒 Security Notice

**IMPORTANT:**
- Your `.ovpn` file contains private keys - keep it secure!
- Never share your VPN configuration file with anyone
- Report lost or compromised files immediately to IT
- Use only on trusted devices

---

## 📥 What You Received

You should have received a file named: `emp-XXXXX.ovpn`

This single file contains everything you need to connect to the VPN:
- Server address
- Your personal certificate
- Encryption keys
- Connection settings

---

## 💻 Installation Instructions

### Windows

**1. Download OpenVPN Client**
- Visit: https://openvpn.net/community-downloads/
- Download "OpenVPN Connect" for Windows
- Run the installer (requires administrator rights)

**2. Import Configuration**
- Open OpenVPN Connect
- Click "+" or "Import Profile"
- Select your `.ovpn` file
- Click "Add"

**3. Connect**
- Click on your profile name
- Click "Connect"
- You're connected when you see "Connected" status

---

### macOS

**1. Download Tunnelblick**
- Visit: https://tunnelblick.net/downloads.html
- Download and install Tunnelblick
- Follow the installation wizard

**2. Import Configuration**
- Double-click your `.ovpn` file
- Tunnelblick will ask to install the configuration
- Click "OK" and enter your Mac password

**3. Connect**
- Click the Tunnelblick icon in menu bar
- Select your configuration
- Click "Connect"

---

### Linux (Ubuntu/Debian)

**1. Install OpenVPN**
```bash
sudo apt update
sudo apt install openvpn
```

**2. Import Configuration**
```bash
# Copy your .ovpn file to OpenVPN directory
sudo cp emp-XXXXX.ovpn /etc/openvpn/client/tbaps.conf

# Or connect directly
sudo openvpn --config emp-XXXXX.ovpn
```

**3. Connect (as service)**
```bash
# Start VPN
sudo systemctl start openvpn-client@tbaps

# Check status
sudo systemctl status openvpn-client@tbaps

# Auto-start on boot
sudo systemctl enable openvpn-client@tbaps
```

---

### iOS (iPhone/iPad)

**1. Download OpenVPN Connect**
- Open App Store
- Search for "OpenVPN Connect"
- Install the official OpenVPN app

**2. Import Configuration**
- Email yourself the `.ovpn` file (use company email)
- Open email on your iOS device
- Tap the `.ovpn` file attachment
- Choose "Copy to OpenVPN"

**3. Connect**
- Open OpenVPN Connect
- Tap the toggle switch next to your profile
- Allow VPN configuration when prompted

---

### Android

**1. Download OpenVPN Connect**
- Open Google Play Store
- Search for "OpenVPN Connect"
- Install the official OpenVPN app

**2. Import Configuration**
- Transfer `.ovpn` file to your device
- Open OpenVPN Connect
- Tap "+" and select "Import"
- Choose "File" and select your `.ovpn` file

**3. Connect**
- Tap your profile name
- Tap "Connect"
- Allow VPN connection when prompted

---

## ✅ Verifying Connection

Once connected, verify your VPN is working:

**1. Check VPN Status**
- Your VPN client should show "Connected"
- You should see a VPN icon in your system tray/menu bar

**2. Check Your IP Address**
- Visit: https://whatismyipaddress.com
- You should see the company's IP address, not your home IP

**3. Test Internal Access**
- Try accessing internal company resources
- Contact IT if you cannot access expected resources

---

## 🔧 Troubleshooting

### Cannot Connect

**Check your internet connection**
- Ensure you have active internet access
- Try accessing a website

**Firewall blocking VPN**
- VPN uses UDP port 1194
- Check if your network blocks this port
- Try from a different network

**Certificate expired**
- Contact IT for a new certificate
- Certificates are valid for 365 days

### Connected but Cannot Access Resources

**DNS issues**
- Disconnect and reconnect
- Restart your VPN client
- Contact IT support

**Routing issues**
- Ensure "redirect gateway" is enabled
- Check your VPN client settings

### Slow Connection

**Normal behavior**
- VPN adds encryption overhead
- Some speed reduction is expected

**Optimize connection**
- Close unnecessary applications
- Use wired connection instead of WiFi
- Try connecting at different times

---

## 📞 Support

**Need Help?**
- Email: it-support@company.com
- Phone: +1 (555) 123-4567
- Slack: #it-support
- Hours: Monday-Friday, 9 AM - 5 PM EST

**Emergency After Hours:**
- Phone: +1 (555) 123-9999

---

## 🔐 Security Best Practices

**DO:**
- ✅ Connect to VPN when accessing company resources
- ✅ Disconnect when not needed
- ✅ Keep your `.ovpn` file secure
- ✅ Use VPN on trusted devices only
- ✅ Report suspicious activity

**DON'T:**
- ❌ Share your VPN configuration
- ❌ Use VPN on public/shared computers
- ❌ Leave VPN connected 24/7 unnecessarily
- ❌ Bypass VPN to access company resources
- ❌ Install VPN on personal devices without approval

---

## 📊 Connection Details

**Server Information:**
- Protocol: UDP
- Port: 1194
- Encryption: AES-256-CBC
- Authentication: SHA256
- TLS Version: 1.2+

**Your Certificate:**
- Validity: 365 days from issue date
- Renewal: Automatic (you'll receive new file)
- Revocation: Immediate upon offboarding

---

## 🔄 Certificate Renewal

**Automatic Renewal:**
- You'll receive a new `.ovpn` file before expiration
- Import the new file using the same steps
- Old certificate will be automatically revoked

**Manual Renewal:**
- Contact IT if you don't receive renewal
- Request new certificate 30 days before expiration

---

## 📱 Multiple Devices

**Can I use VPN on multiple devices?**
- Yes! Import your `.ovpn` file on each device
- You can connect from multiple devices simultaneously
- Each connection is logged for security

**Device Recommendations:**
- Work laptop: ✅ Recommended
- Personal laptop: ⚠️ With approval
- Work phone: ✅ Recommended
- Personal phone: ⚠️ With approval
- Public computers: ❌ Never

---

## 🌍 International Travel

**Using VPN while traveling:**
- ✅ VPN works from anywhere in the world
- ⚠️ Some countries restrict VPN use
- ⚠️ Hotel/public WiFi may block VPN ports
- ✅ Always use VPN on public WiFi

**Blocked in your location?**
- Contact IT for alternative access methods
- May need to use different port or protocol

---

## 📝 Frequently Asked Questions

**Q: Do I need to be connected to VPN all the time?**
A: No, only when accessing company resources.

**Q: Can I access the internet through VPN?**
A: Yes, all traffic is routed through the VPN for security.

**Q: Will VPN slow down my internet?**
A: Slightly, due to encryption overhead. Usually not noticeable.

**Q: What happens if I lose my .ovpn file?**
A: Contact IT immediately. We'll revoke it and issue a new one.

**Q: Can I use free VPN services instead?**
A: No, you must use the company VPN for security compliance.

**Q: My certificate expired, what do I do?**
A: Contact IT for a new certificate. Don't wait until expiration!

---

## 📧 Feedback

We're always improving! Send feedback to: vpn-feedback@company.com

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-28  
**Maintained By:** TBAPS Infrastructure Team
