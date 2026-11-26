---
name: homelab-network-suite
description: >
  Self-hosted homelab engineering: network readiness, VLAN segmentation, Pi-hole DNS filtering, WireGuard mesh VPN tunnels, firewall rules, and local cluster infrastructure.
category: devops_security
version: "2.0.0"
role: consolidated_suite
triggers: homelab-network-suite, homelab infrastructure, networking & vpn suite, homelab, homelab-network-readiness, homelab-network-setup, homelab-pihole-dns, homelab-vlan-segmentation, homelab-wireguard-vpn
---

# 🏠 Homelab Infrastructure, Networking & VPN Suite

Self-hosted homelab engineering: network readiness, VLAN segmentation, Pi-hole DNS filtering, WireGuard mesh VPN tunnels, firewall rules, and local cluster infrastructure.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (5 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`homelab-network-readiness`**: Readiness checklist for homelab VLAN segmentation, local DNS filtering (Pi-hole, AdGuard Home), and WireGuard-style remote access. Use when planning or reviewing home network changes — splitting a flat network into trusted, IoT, guest, or management VLANs, moving DHCP to a local resolver, or adding VPN access — before changing router, firewall, DHCP, or VPN configuration.
  - *Reference File:* `references/homelab-network-readiness.md`
- **`homelab-network-setup`**: Practical home and homelab network planning for gateways, switches, access points, IP ranges, DHCP reservations, DNS, cabling, and common beginner mistakes. Use when planning or fixing a home or homelab network — gateway, switch, AP, IP ranges, DHCP, DNS, or cabling.
  - *Reference File:* `references/homelab-network-setup.md`
- **`homelab-pihole-dns`**: Pi-hole installation, blocklist management, DNS-over-HTTPS setup, DHCP integration, local DNS records, and troubleshooting broken DNS resolution on a home network. Use when the task explicitly involves Pi-hole — installing it, managing blocklists, configuring DoH or DHCP, adding local DNS records, or diagnosing DNS resolution with Pi-hole in the path.
  - *Reference File:* `references/homelab-pihole-dns.md`
- **`homelab-vlan-segmentation`**: Segmenting home networks into VLANs for IoT, guest, trusted, and server traffic using UniFi, pfSense/OPNsense, and MikroTik — including switch trunk config, firewall rules, and wireless SSID mapping. Use when splitting a home network into IoT, guest, trusted, and server VLANs on UniFi, pfSense/OPNsense, or MikroTik.
  - *Reference File:* `references/homelab-vlan-segmentation.md`
- **`homelab-wireguard-vpn`**: WireGuard VPN server setup, peer configuration, key generation, split tunneling vs full tunnel routing, and remote access to a home network from mobile and laptop clients. Use when setting up WireGuard for remote access to a home network, or deciding between split and full tunnel routing.
  - *Reference File:* `references/homelab-wireguard-vpn.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `homelab-network-readiness`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
