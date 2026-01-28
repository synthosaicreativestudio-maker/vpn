---
name: Security & Hacking
description: VPN protocols, network analysis, censorship bypass, OSINT, server hardening
version: 1.0.0
---

# Security & Hacking Skills

## Available Skills

| Skill | Description |
|-------|-------------|
| [vpn_protocols.md](vpn_protocols.md) | VLESS, REALITY, WireGuard protocols |
| [network_diagnostics.md](network_diagnostics.md) | Network analysis, tcpdump, ss, nmap |
| [censorship_evasion.md](censorship_evasion.md) | DPI bypass, SNI masking, stealth |
| [osint_recon.md](osint_recon.md) | IP analysis, leak detection, Shodan |
| [server_hardening.md](server_hardening.md) | SSH, firewall, fail2ban, updates |

## Quick Reference

### VPN Debugging
1. Check port: `ss -tlnp | grep 443`
2. Check SNI matches server config
3. Verify UUID and public key
4. Test with: `curl -x socks5://127.0.0.1:1080 https://ip-api.com`

### Leak Test
```bash
curl https://ip-api.com/json | jq
# Use browser: https://ipleak.net
```

### Server Security
```bash
ufw status
fail2ban-client status sshd
docker ps
```

## Instructions
- Reference specific skill files for detailed commands
- Use network_diagnostics for connection issues
- Use censorship_evasion for blocked access
- Use osint_recon for leak testing
- Use server_hardening for security setup
