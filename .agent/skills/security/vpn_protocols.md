---
name: VPN Protocols
description: Deep knowledge of VPN protocols - VLESS, REALITY, WireGuard, OpenVPN, Shadowsocks
version: 1.0.0
---

# VPN Protocols

## Core Knowledge

### VLESS + REALITY
- **VLESS**: Lightweight protocol without encryption overhead (relies on TLS)
- **REALITY**: Advanced TLS fingerprint masking, mimics real websites
- **SNI (Server Name Indication)**: Critical for REALITY, must match trusted site
- **Flow**: `xtls-rprx-vision` for best performance
- **Fingerprint**: `chrome`, `firefox`, `safari` for browser emulation

### Key Parameters
```
Protocol: VLESS
Port: 443 (standard HTTPS)
Security: REALITY
SNI: Must be accessible and trusted (e.g., taxi.yandex.ru)
Public Key: Server's x25519 public key
Flow: xtls-rprx-vision
Fingerprint: chrome/firefox/safari
```

### WireGuard
- UDP-based, fastest VPN protocol
- Port: Default 51820
- Uses Curve25519 for keys
- Simple config: PrivateKey, PublicKey, Endpoint, AllowedIPs

### Common Issues & Fixes
1. **Connection refused**: Check port 443 open, Xray running
2. **TLS handshake failed**: SNI mismatch or wrong public key
3. **Slow speed**: Wrong flow setting, use xtls-rprx-vision
4. **Detection by DPI**: Change SNI to popular local site

## Commands Reference

```bash
# Generate REALITY keys
docker exec marzban xray x25519

# Check Xray listening
ss -tlnp | grep 443

# View Xray logs
docker logs marzban -f | grep -i error

# Test VLESS connection
curl -v --proxy socks5://127.0.0.1:1080 https://ip-api.com
```

## Client Config Formats
- **Xray/V2Ray**: JSON with outbounds[]
- **Sing-box**: JSON with outbounds[], different syntax
- **Clash**: YAML with proxies[]
- **URL Sharing**: `vless://uuid@server:port?params#name`

## Instructions
- Always verify SNI matches server config before troubleshooting
- Check if port 443 is open and not blocked by ISP
- Verify UUID and public key are correct
- Use smart routing to bypass local sites for better performance
