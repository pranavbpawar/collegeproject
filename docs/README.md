# Intelligent Zero-Trust Security System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## 🎯 Overview

An enterprise-grade intelligent cybersecurity platform that integrates **Zero-Trust Architecture**, **Network Telemetry Analysis**, and **Adaptive Machine Learning** to detect, predict, and respond to security threats in real-time.

### Key Capabilities

- 🔒 **Zero-Trust Security**: Identity-first, continuous verification, least privilege access
- 🌐 **Network Intelligence**: Real-time traffic analysis, VPN monitoring, anomaly detection
- 🤖 **Adaptive ML**: Behavioral profiling, anomaly detection, dynamic risk scoring
- ⚡ **Automated Response**: Intelligent threat mitigation with explainable decisions
- 📊 **Real-Time Dashboard**: Live monitoring, alerts, and threat visualization
- 🔌 **Enterprise Integration**: REST API, WebSocket streaming, SIEM connectors

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Dashboard & API (Presentation Layer)            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│         Orchestration Engine (Decision & Response)           │
│    • Risk Scoring  • Policy Engine  • Response Manager       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────┬──────────────────┬─────────────────────────┐
│   Security   │    Network       │   Machine Learning      │
│     Layer    │     Layer        │       Layer             │
│              │                  │                         │
│ • Zero Trust │ • Traffic        │ • Behavioral Profiling  │
│ • Identity   │   Analysis       │ • Anomaly Detection     │
│ • Access     │ • Flow Metrics   │ • Time Series Analysis  │
│   Control    │ • DNS/VPN Logs   │ • Risk Prediction       │
└──────────────┴──────────────────┴─────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Data Collection (Agents & Collectors)           │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Docker & Docker Compose (optional, for containerized deployment)
- 8GB+ RAM recommended
- Linux/macOS (Windows with WSL2)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd MACHINE

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate certificates for secure communication
bash scripts/generate_certs.sh

# Initialize system
bash scripts/setup.sh
```

### Running the System

**Option 1: Docker Compose (Recommended)**
```bash
docker-compose up -d
```

**Option 2: Manual Start**
```bash
# Start API server
python src/api/main.py

# Start ML engine (in another terminal)
python src/ml/model_trainer.py --mode serve

# Start dashboard
cd src/dashboard && python -m http.server 8080
```

Access the dashboard at: `http://localhost:8080`

## 🏢 Self-Hosted Infrastructure (TBAPS Production)

### Complete On-Premise Deployment

TBAPS now includes a **production-ready self-hosted infrastructure** with **zero cloud dependencies**. Perfect for organizations requiring complete data sovereignty and on-premise deployment.

#### 🎯 Key Features

- ✅ **100% On-Premise** - All data stays on your servers
- ✅ **11 Services** - PostgreSQL, Redis, RabbitMQ, FastAPI, React, Nginx, Prometheus, Grafana, OpenVPN, Backup
- ✅ **Automated Backups** - Daily encrypted backups with 30-day retention
- ✅ **High Availability** - Service replication and health checks
- ✅ **Security Hardened** - TLS 1.2+, AES-256 encryption, firewall, Fail2Ban
- ✅ **Monitoring** - Prometheus metrics + Grafana dashboards
- ✅ **VPN Access** - OpenVPN for secure remote access
- ✅ **Scalable** - Supports 500+ employees, scales to 1000+
- ✅ **Cost-Effective** - ~$3,600 initial + $250/month vs $2,000-5,000/month cloud

#### 🚀 Quick Deploy

```bash
# 1. Configure environment
cp .env.example .env
nano .env  # Update passwords and domain

# 2. Deploy all services
docker compose -f docker-compose.production.yml up -d

# 3. Initialize database
docker compose -f docker-compose.production.yml exec backend python manage.py migrate

# 4. Create admin user
docker compose -f docker-compose.production.yml exec backend python manage.py createsuperuser

# 5. Access application
https://tbaps.yourcompany.local
```

#### 📖 Infrastructure Documentation

| Document | Description |
|----------|-------------|
| [**Infrastructure Delivery**](INFRASTRUCTURE-DELIVERY.md) | Complete delivery summary and validation |
| [**Visual Overview**](docs/visual-overview.md) | ASCII diagrams of architecture and data flow |
| [**Infrastructure Setup**](docs/infrastructure-setup.md) | Hardware, network, security, backup, monitoring |
| [**Deployment Checklist**](docs/deployment-checklist.md) | Step-by-step deployment and verification |
| [**Quick Start Guide**](docs/quick-start.md) | Common commands and troubleshooting |

#### 🔧 Management Scripts

```bash
# Automated backup (runs daily at 2 AM)
sudo ./scripts/backup/backup.sh

# Restore from backup
sudo ./scripts/backup/restore.sh /srv/backups/postgres/backup_file.sql.gz.enc

# Health check
./scripts/monitoring/health-check.sh

# View service status
docker compose -f docker-compose.production.yml ps

# View logs
docker compose -f docker-compose.production.yml logs -f
```

#### 💰 Cost Comparison

| Deployment | Initial Cost | Monthly Cost | Annual Cost |
|------------|--------------|--------------|-------------|
| **Self-Hosted** | $3,630 | $250 | $6,630 (Year 1) |
| **AWS/Azure/GCP** | $0 | $2,000-5,000 | $24,000-60,000 |
| **Savings** | - | - | **$17,000-54,000/year** |

#### 🔒 Security Features

- **Network:** Firewall (UFW), VPN (OpenVPN), Network isolation
- **Transport:** TLS 1.2+, SSL certificates, Perfect forward secrecy
- **Application:** JWT auth, Rate limiting, CORS, Input validation
- **Data:** AES-256 encryption, Password protection, Backup encryption
- **Access:** SSH keys only, Fail2Ban, RBAC, Audit logging

#### 📊 Monitoring & Alerts

- **Prometheus** - Metrics collection from all services
- **Grafana** - Pre-configured dashboards for system, application, and security monitoring
- **Alerts** - Email notifications for high CPU, memory, disk, service failures, and security events

#### 🔄 Backup & Recovery

- **Automated Backups:** Daily at 2 AM with AES-256 encryption
- **Retention:** 30 days
- **Components:** PostgreSQL, Redis, Application data, Configuration
- **RTO:** 4 hours | **RPO:** 24 hours

## 📚 Documentation

- [Architecture Documentation](docs/architecture.md) - Detailed system design
- [Threat Modeling](docs/threat_modeling.md) - Attack scenarios and defenses
- [Dataset Design](docs/dataset_design.md) - Feature engineering and data schema
- [Research Paper](docs/research_paper.md) - Academic documentation
- [Deployment Guide](docs/deployment_guide.md) - Production deployment

## 🔬 Use Cases

### Enterprise Security Operations Center (SOC)
- Real-time threat detection across corporate network
- Insider threat monitoring and prevention
- Automated incident response and investigation

### Remote Workforce Protection
- VPN and remote access monitoring
- Geographic anomaly detection
- Device posture assessment

### Cloud Security
- Multi-cloud environment monitoring
- API abuse detection
- Lateral movement prevention

### Critical Infrastructure
- Industrial control system (ICS) protection
- Operational technology (OT) network monitoring
- Supply chain security

## 🧪 Testing & Evaluation

```bash
# Run all tests
pytest tests/ -v --cov=src

# Run threat scenarios
python tests/scenarios/run_all_scenarios.py

# Evaluate ML models
python tests/evaluation/evaluate_models.py

# Performance benchmarks
python tests/evaluation/benchmark.py
```

### Performance Metrics

- **Detection Accuracy**: >95% on test scenarios
- **False Positive Rate**: <2%
- **Detection Latency**: <5 seconds for critical threats
- **Throughput**: 10,000+ events/second
- **API Response Time**: <200ms (95th percentile)

## 🔧 Configuration

Main configuration file: `config/default.yaml`

```yaml
security:
  zero_trust:
    mfa_required: true
    session_timeout: 3600
    
ml:
  models:
    anomaly_detection:
      algorithm: "isolation_forest"
      contamination: 0.01
      
network:
  monitoring:
    interfaces: ["eth0", "wlan0"]
    capture_filter: "tcp or udp"
```

## 🔌 API Integration

### REST API

```python
import requests

# Get user risk score
response = requests.get(
    "http://localhost:8000/api/v1/risk/user/john.doe",
    headers={"Authorization": f"Bearer {token}"}
)
risk_score = response.json()["risk_score"]
```

### WebSocket (Real-time Events)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/events');
ws.onmessage = (event) => {
    const alert = JSON.parse(event.data);
    console.log('New threat:', alert);
};
```

## 🛡️ Security & Ethics

This system is designed for **defensive security research** and **authorized network monitoring** only.

### Legal & Compliance
- ✅ Obtain proper authorization before deployment
- ✅ Comply with privacy regulations (GDPR, CCPA)
- ✅ Implement data retention policies
- ✅ Maintain audit logs for all security decisions
- ✅ Ensure user consent and transparency

### Responsible Use
- ❌ Do not use for unauthorized surveillance
- ❌ Do not deploy without legal authorization
- ❌ Do not violate privacy rights
- ✅ Use only for legitimate security purposes
- ✅ Follow ethical hacking guidelines

## 📊 System Components

### Security Layer
- `src/security/zero_trust.py` - Zero-trust architecture
- `src/security/identity_manager.py` - Identity & access management
- `src/security/threat_detector.py` - Threat detection engine

### Network Layer
- `src/network/traffic_analyzer.py` - Traffic analysis
- `src/network/vpn_monitor.py` - VPN monitoring
- `src/network/network_anomaly.py` - Network anomaly detection

### Machine Learning Layer
- `src/ml/behavioral_profiler.py` - Behavioral profiling
- `src/ml/anomaly_detector.py` - ML anomaly detection
- `src/ml/risk_scorer.py` - Dynamic risk scoring
- `src/ml/model_trainer.py` - Model training pipeline

### Orchestration
- `src/core/orchestrator.py` - Central orchestration
- `src/core/policy_engine.py` - Policy management
- `src/core/response_manager.py` - Automated response
- `src/core/explainability.py` - Decision explainability

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and code of conduct.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- MITRE ATT&CK Framework for threat modeling
- NIST Cybersecurity Framework for security controls
- Open-source ML and security communities

## 📧 Contact

For questions, issues, or collaboration opportunities, please open an issue on GitHub.

---

**⚠️ Disclaimer**: This software is provided for educational and authorized security research purposes only. Users are responsible for ensuring compliance with all applicable laws and regulations.
