---
name: pi-alert
description: >
  Local network intruder detection and security monitoring. Discovers new IP/MAC devices, scans open ports, alerts on unknown connections, and monitors offline services.
metadata:
  version: "1.0.0"
  category: devops_security
  triggers: pi-alert, network monitor, intruder detector, arp scan, lan security, wifi alert
---

# Pi.Alert — Network Security & Intruder Detection

Orchestrates local network surveillance using Pi.Alert. Continuously probes ARP tables, DNS records, and active IP leases to maintain an authoritative hardware registry.

## Monitoring Capabilities
- **New Device Alerts**: Flags any new MAC address joining the Wi-Fi/LAN network.
- **Port Scanner**: Detects exposed internal management ports (SSH, Telnet, HTTP, SMB).
- **Presence Tracking**: Logs device connection timelines to detect network anomalies.
