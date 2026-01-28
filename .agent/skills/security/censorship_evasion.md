---
name: Censorship Evasion
description: Techniques to bypass DPI, firewalls, and network censorship
version: 1.0.0
---

# Censorship Evasion

## Core Concepts

### Deep Packet Inspection (DPI) Bypass
DPI analyzes packet contents to identify VPN traffic. Evasion methods:

1. **TLS Fingerprint Masking (REALITY)**
   - Mimics legitimate TLS handshake of real websites
   - Uses actual website certificates as camouflage
   - Choose SNI wisely: popular, accessible, not blocked

2. **Domain Fronting**
   - Use CDN domain (e.g., cloudflare.com) as visible SNI
   - Actual destination hidden in HTTP Host header
   - Being blocked by many CDN providers now

3. **Protocol Obfuscation**
   - **obfs4**: Makes traffic look random
   - **Shadowsocks-AEAD**: Lightweight, fast
   - **Cloak**: Plugin for Shadowsocks, mimics HTTPS

### Best SNI Choices for Russia
```
# High-trust domains (low block probability)
taxi.yandex.ru      # Yandex Taxi - essential service
ya.ru               # Yandex main
vk.com              # VKontakte
mail.ru             # Mail.ru

# Avoid these
www.microsoft.com   # Often flagged/analyzed
google.com          # May have specific DPI rules
cloudflare.com      # Known for CDN abuse
```

### uTLS Fingerprints
```
# Available fingerprints for VPN clients
chrome      # Most common, recommended
firefox     # Good alternative
safari      # For Apple device imitation
edge        # Windows Edge
ios         # iOS Safari
android     # Android Chrome
random      # Randomized (may trigger detection)
```

## Detection Vectors & Countermeasures

| Detection Method | Countermeasure |
|-----------------|----------------|
| SNI-based blocking | Use allowed SNI (taxi.yandex.ru) |
| Port blocking | Use 443 (standard HTTPS) |
| TLS fingerprint | Use REALITY with chrome fp |
| Timing analysis | Enable traffic padding |
| Protocol signatures | Use VLESS (minimal signature) |
| Active probing | REALITY responds as real server |

## Smart Routing for Stealth

Route local traffic directly to avoid triggering monitoring:
```json
{
  "rules": [
    {"domain_suffix": [".ru", ".рф"], "outbound": "direct"},
    {"geosite": ["yandex", "vk", "mailru"], "outbound": "direct"},
    {"ip_cidr": ["77.88.0.0/16"], "outbound": "direct"}
  ]
}
```

Benefits:
- Less VPN traffic = less attention
- Russian services work at full speed
- Monitoring sees normal local traffic pattern

## Testing Censorship

```bash
# Check if port is blocked
curl -v --connect-timeout 5 https://37.1.212.51:443

# Check TLS handshake
openssl s_client -connect 37.1.212.51:443 -servername taxi.yandex.ru

# Check from different networks
# Use mobile data vs WiFi to compare
```

## Instructions
- Always use SNI matching local trusted services
- Prefer port 443 (HTTPS) over custom ports
- Use chrome fingerprint for most cases
- Implement smart routing to reduce VPN traffic volume
- Test connection from restricted networks regularly
