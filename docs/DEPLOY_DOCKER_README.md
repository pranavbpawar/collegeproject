# TBAPS Automated Docker Deployment

## 🚀 One-Command Deployment

Deploy the entire TBAPS system with a single command using Docker.

---

## 📋 Prerequisites

Before running the deployment script, ensure you have:

### Required Software
- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Git** 2.0+
- **OpenSSL** 1.1.1+
- **OpenVPN** 2.5+

### System Requirements
- **OS:** Linux (Ubuntu 20.04+, Debian 11+)
- **RAM:** 8GB minimum
- **Disk:** 20GB free space
- **Permissions:** Sudo access

---

## 📥 Quick Install Prerequisites

### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install all prerequisites
sudo apt install -y docker.io docker-compose git openssl openvpn

# Add user to docker group
sudo usermod -aG docker $USER

# Apply group changes (logout/login or run)
newgrp docker

# Verify installations
docker --version
docker-compose --version
git --version
openssl version
openvpn --version
```

---

## 🎯 Usage

### Basic Deployment

```bash
# Navigate to project directory
cd ~/Desktop/MACHINE

# Run deployment script
./deploy-docker.sh
```

That's it! The script will:
1. ✅ Check all prerequisites
2. ✅ Create directory structure
3. ✅ Generate environment configuration
4. ✅ Start PostgreSQL database
5. ✅ Initialize database schemas
6. ✅ Setup VPN infrastructure
7. ✅ Generate CA certificates
8. ✅ Start VPN services
9. ✅ Start backend API
10. ✅ Verify complete deployment

---

## ⚙️ Configuration

### Change VPN Server IP

Edit the script before running:

```bash
nano deploy-docker.sh

# Find and change this line:
VPN_SERVER_IP="127.0.0.1"  # Change to your public IP

# For example:
VPN_SERVER_IP="192.168.1.100"  # Local network
VPN_SERVER_IP="203.0.113.1"    # Public IP
```

### Change Database Password

```bash
nano deploy-docker.sh

# Find and change this line:
POSTGRES_PASSWORD="tbaps_secure_password_2026"

# Change to your secure password:
POSTGRES_PASSWORD="your_secure_password_here"
```

---

## 📊 What Gets Deployed

### Services Started

1. **PostgreSQL Database**
   - Port: 5432
   - User: tbaps
   - Database: tbaps
   - Tables: 10+ tables created

2. **OpenVPN Server**
   - Port: 1194/UDP
   - Encryption: AES-256-CBC
   - Authentication: SHA256

3. **VPN Logger**
   - Monitors connections
   - Logs to PostgreSQL

4. **Backend API** (if configured)
   - Port: 8000
   - FastAPI application
   - REST endpoints

### Files Created

```
.env                              # Environment variables
/srv/tbaps/vpn/ca/ca.crt         # CA certificate
/srv/tbaps/vpn/ca/ca.key         # CA private key
/srv/tbaps/vpn/ta.key            # TLS auth key
/srv/tbaps/vpn/config/server_ip.txt  # Server IP
/var/log/tbaps/                   # Log directory
```

---

## 🧪 Testing After Deployment

### Test Backend API

```bash
# Health check
curl http://localhost:8000/health

# Expected output:
# {"status":"healthy"}
```

### Test Database

```bash
# Connect to PostgreSQL
docker-compose exec postgresql psql -U tbaps -d tbaps

# List tables
\dt

# Exit
\q
```

### Generate Test Certificate

```bash
# Navigate to scripts
cd vpn/scripts

# Generate certificate
./generate-nef-certificate.sh "Test User" "test@company.com"

# Check certificate created
ls -lh /srv/tbaps/vpn/configs/test_user.nef
```

### View API Documentation

```bash
# Open in browser
http://localhost:8000/docs
```

---

## 🔧 Management Commands

### View Running Services

```bash
# List all containers
docker-compose ps

# List VPN services
docker-compose -f docker-compose.vpn.yml ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgresql
docker-compose logs -f backend

# VPN services
docker-compose -f docker-compose.vpn.yml logs -f openvpn
docker-compose -f docker-compose.vpn.yml logs -f vpn-logger
```

### Stop Services

```bash
# Stop all services
docker-compose down
docker-compose -f docker-compose.vpn.yml down
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart postgresql
docker-compose restart backend
```

### Start Services (After Stop)

```bash
# Start all services
docker-compose up -d
docker-compose -f docker-compose.vpn.yml up -d
```

---

## 🌐 Access Points

After successful deployment:

| Service | URL/Address | Credentials |
|---------|-------------|-------------|
| **Backend API** | http://localhost:8000 | N/A |
| **API Docs** | http://localhost:8000/docs | N/A |
| **Database** | localhost:5432 | User: tbaps<br>Pass: tbaps_secure_password_2026<br>DB: tbaps |
| **VPN Server** | 127.0.0.1:1194 | Certificate-based |

---

## 📁 Directory Structure

```
~/Desktop/MACHINE/
├── deploy-docker.sh              # Deployment script
├── .env                          # Environment variables
├── docker-compose.yml            # Main services
├── docker-compose.vpn.yml        # VPN services
├── backend/                      # Backend application
├── vpn/                          # VPN management
│   ├── scripts/                  # Management scripts
│   ├── database/                 # Database schemas
│   └── docs/                     # Documentation

/srv/tbaps/vpn/
├── ca/                           # Certificate Authority
│   ├── ca.crt                    # CA certificate
│   └── ca.key                    # CA private key
├── certs/                        # Individual certificates
├── configs/                      # Generated .nef files
├── config/                       # Configuration
│   └── server_ip.txt             # VPN server IP
└── ta.key                        # TLS auth key

/var/log/tbaps/                   # Application logs
```

---

## 🐛 Troubleshooting

### Script Fails: Missing Dependencies

```bash
# Install missing dependencies
sudo apt update
sudo apt install -y docker.io docker-compose git openssl openvpn

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Script Fails: Permission Denied

```bash
# Make script executable
chmod +x deploy-docker.sh

# Run with sudo if needed
sudo ./deploy-docker.sh
```

### PostgreSQL Won't Start

```bash
# Check if port 5432 is in use
sudo netstat -tulpn | grep 5432

# Stop conflicting service
sudo systemctl stop postgresql

# Restart deployment
./deploy-docker.sh
```

### Backend API Not Responding

```bash
# Check if backend service exists
docker-compose ps backend

# View backend logs
docker-compose logs backend

# Manually start backend
docker-compose up -d backend
```

### VPN Services Not Starting

```bash
# Check VPN compose file exists
ls -la docker-compose.vpn.yml

# View VPN logs
docker-compose -f docker-compose.vpn.yml logs

# Restart VPN services
docker-compose -f docker-compose.vpn.yml restart
```

### Port Already in Use

```bash
# Find what's using the port
sudo lsof -i :8000  # Backend
sudo lsof -i :5432  # PostgreSQL
sudo lsof -i :1194  # VPN

# Kill the process or change port in docker-compose.yml
```

---

## 🔄 Redeployment

### Clean Redeployment

```bash
# Stop all services
docker-compose down -v
docker-compose -f docker-compose.vpn.yml down -v

# Remove generated files (optional)
rm -f .env
sudo rm -rf /srv/tbaps/vpn/ca/*
sudo rm -rf /srv/tbaps/vpn/configs/*

# Run deployment again
./deploy-docker.sh
```

### Update Deployment

```bash
# Pull latest changes
git pull

# Restart services
docker-compose down
docker-compose up -d

docker-compose -f docker-compose.vpn.yml down
docker-compose -f docker-compose.vpn.yml up -d
```

---

## 📝 Daily Operations

### Generate Employee Certificate

```bash
cd vpn/scripts
./generate-nef-certificate.sh "Employee Name" "email@company.com"
```

### Onboard New Employee

```bash
cd vpn/scripts
./onboard-employee-with-nef.sh
```

### Batch Generate Certificates

```bash
# Create CSV file
cat > employees.csv << EOF
name,email,department,role
John Doe,john@company.com,Engineering,Developer
Jane Smith,jane@company.com,Sales,Manager
EOF

# Run batch generation
cd vpn/scripts
./batch-generate-nef-certificates.sh employees.csv
```

### Database Backup

```bash
# Backup database
docker-compose exec -T postgresql pg_dump -U tbaps tbaps > backup_$(date +%Y%m%d).sql

# Restore database
docker-compose exec -T postgresql psql -U tbaps tbaps < backup_20260128.sql
```

---

## 📊 Deployment Script Features

### ✅ Automated Checks
- Prerequisite verification
- Dependency checking
- User permissions validation

### ✅ Intelligent Setup
- Directory structure creation
- Environment configuration
- Secure password generation

### ✅ Service Management
- PostgreSQL initialization
- Database schema loading
- VPN infrastructure setup
- Backend API startup

### ✅ Verification
- Service health checks
- Database connectivity tests
- API endpoint validation

### ✅ User-Friendly Output
- Color-coded messages
- Progress indicators
- Detailed summary
- Next steps guidance

---

## 🎯 Deployment Time

**Total Time:** 5-10 minutes

**Breakdown:**
- Prerequisite check: 10 seconds
- Directory setup: 5 seconds
- PostgreSQL start: 15 seconds
- Database initialization: 30 seconds
- VPN setup: 2 minutes
- Service startup: 1 minute
- Verification: 30 seconds

---

## 🔒 Security Notes

### Development
- Default passwords are used
- Debug mode enabled
- Services on localhost
- For testing only

### Production
Before deploying to production:

1. **Change passwords** in the script
2. **Update VPN_SERVER_IP** to public IP
3. **Disable debug mode** in .env
4. **Configure firewall** rules
5. **Enable SSL/TLS** for API
6. **Set up monitoring**
7. **Configure backups**

---

## 📚 Additional Resources

- **Full Guide:** LOCAL_DEPLOYMENT_GUIDE.md
- **Architecture:** DEPLOYMENT_MAP.md
- **VPN Details:** VPN_INFRASTRUCTURE_DELIVERY.md
- **Native Deploy:** NATIVE_DEPLOYMENT_GUIDE.md
- **API Docs:** http://localhost:8000/docs (after deployment)

---

## ✅ Success Criteria

After running the script, you should see:

```
✓ All prerequisites satisfied
✓ Directories created
✓ Environment file created
✓ PostgreSQL is running
✓ VPN infrastructure schema loaded
✓ NEF certificate schema loaded
✓ Database initialized with 10+ tables
✓ CA certificate generated
✓ TLS auth key generated
✓ VPN services are running
✓ Backend API: Responding on port 8000
✓ PostgreSQL: Connected
✓ OpenVPN: Running

DEPLOYMENT COMPLETED SUCCESSFULLY!
```

---

## 🎉 Quick Start

```bash
# 1. Install prerequisites
sudo apt install -y docker.io docker-compose git openssl openvpn

# 2. Add user to docker group
sudo usermod -aG docker $USER && newgrp docker

# 3. Navigate to project
cd ~/Desktop/MACHINE

# 4. Run deployment
./deploy-docker.sh

# 5. Test deployment
curl http://localhost:8000/health

# 6. Generate test certificate
cd vpn/scripts && ./generate-nef-certificate.sh "Test User" "test@company.com"
```

---

**Status:** ✅ READY TO USE  
**Version:** 1.0.0  
**Last Updated:** 2026-01-28

**🎉 Deploy TBAPS with one command! 🎉**
