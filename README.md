# DHCP Server

A **production-ready DHCP server implementation** in Python, built from scratch with extensibility and real-world features in mind.

> 🚀 **Active Development** — This project implements the full DHCP protocol (RFC 2131) with modern features like web dashboard, Docker support, and monitoring.

## 🎯 Project Vision

Unlike simple DHCP implementations, this server aims to provide:
- **Full RFC 2131 compliance** (DISCOVER, OFFER, REQUEST, ACK, RELEASE)
- **Enterprise features** (reservations, multiple subnets, relay support)
- **Modern DevOps** (Docker, monitoring, REST API)
- **Educational value** (clean code, well-documented)

## ✨ Current Features

- ✅ UDP socket binding and packet reception
- ✅ JSON-based configuration
- ✅ Structured logging
- 🚧 DHCP packet parsing (in progress)
- 🚧 IP allocation logic (in progress)
- 🚧 Lease management (in progress)

## 🗺️ Roadmap

### Phase 1: Core Protocol ✅ (In Progress)
- [x] Project structure and configuration
- [ ] DHCP packet parsing (RFC 2131)
- [ ] IP address allocation
- [ ] Lease persistence (JSON database)
- [ ] DHCP message types (DISCOVER → OFFER → REQUEST → ACK)

### Phase 2: Production Features 🔄 (Next)
- [ ] MAC address reservations
- [ ] Multiple subnet support
- [ ] Configuration hot-reload
- [ ] File logging with rotation
- [ ] Command-line arguments

### Phase 3: Advanced Features 🔮 (Future)
- [ ] Web dashboard (Flask)
- [ ] REST API for management
- [ ] DHCP relay agent support
- [ ] Docker containerization
- [ ] Prometheus metrics
- [ ] DNS integration

### Phase 4: Quality & DevOps 🎓 (Future)
- [ ] Unit tests (pytest)
- [ ] Integration tests
- [ ] GitHub Actions CI/CD
- [ ] Documentation site
- [ ] Performance benchmarks

## 🛠️ Technology Stack

- **Language:** Python 3.7+
- **Networking:** Standard library (`socket`, `struct`)
- **Configuration:** JSON
- **Future:** Flask (web UI), Docker, Prometheus

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- Administrator/root privileges (for port 67)

### Installation

```bash
git clone git@github.com:saifkhlifikh/dhcp-server.git
cd dhcp-server

# Optional: Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### Configuration

Edit `config.json`:
```json
{
  "server_ip": "192.168.1.1",
  "subnet_mask": "255.255.255.0",
  "gateway": "192.168.1.1",
  "dns_servers": ["8.8.8.8", "8.8.4.4"],
  "ip_pool_start": "192.168.1.100",
  "ip_pool_end": "192.168.1.200",
  "lease_time": 86400
}
```

### Run

```bash
# Linux/Mac (requires sudo for port 67)
sudo python3 dhcp_server.py

# Windows (run PowerShell as Administrator)
python dhcp_server.py
```

## 📖 Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [RFC 2131](https://datatracker.ietf.org/doc/html/rfc2131) - DHCP protocol specification

## 🤝 Contributing

Contributions are welcome! This is an active learning project. See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Branch naming conventions
- Commit message format
- Development workflow
- Code style guidelines

## 📊 Project Stats

![GitHub last commit](https://img.shields.io/github/last-commit/saifkhlifikh/dhcp-server)
![GitHub issues](https://img.shields.io/github/issues/saifkhlifikh/dhcp-server)
![GitHub pull requests](https://img.shields.io/github/issues-pr/saifkhlifikh/dhcp-server)
![License](https://img.shields.io/github/license/saifkhlifikh/dhcp-server)

## 📝 License

MIT License - see [LICENSE](LICENSE) file.

## ⚠️ Disclaimer

This project is under active development. While aiming for production quality, it's primarily educational. For critical production environments, consider mature solutions like:
- **ISC DHCP Server** (industry standard)
- **dnsmasq** (lightweight)
- **Kea DHCP** (modern, from ISC)

## 🙏 Acknowledgments

Built with guidance from:
- RFC 2131 (DHCP Protocol)
- RFC 2132 (DHCP Options)
- Python networking community

---

**⭐ Star this repo if you find it useful!**

**🐛 Found a bug?** [Open an issue](https://github.com/saifkhlifikh/dhcp-server/issues)

**💡 Have ideas?** [Start a discussion](https://github.com/saifkhlifikh/dhcp-server/discussions)