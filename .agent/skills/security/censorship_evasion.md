---
name: Censorship Evasion
description: Techniques to bypass DPI, firewalls, and network censorship
version: 1.0.0
---

# Censorship Evasion

## DPI Bypass Methods

1. **REALITY** — TLS fingerprint masking, mimics real websites
2. **Domain Fronting** — CDN domain as visible SNI
3. **Protocol Obfuscation** — obfs4, Shadowsocks, Cloak

## Best SNI for Russia
```
taxi.yandex.ru    # ✅ Recommended - essential service
ya.ru             # Yandex main
vk.com            # VKontakte
mail.ru           # Mail.ru

# Avoid
www.microsoft.com # Often flagged
google.com        # May have DPI rules
```

## uTLS Fingerprints
```
chrome      # Most common, recommended
firefox     # Good alternative
safari      # Apple device imitation
edge        # Windows Edge
```

## Detection vs Countermeasures

| Detection | Countermeasure |
|-----------|----------------|
| SNI blocking | Use allowed SNI (taxi.yandex.ru) |
| Port blocking | Use 443 (HTTPS) |
| TLS fingerprint | REALITY + chrome fp |
| Active probing | REALITY responds as real server |

## Smart Routing for Stealth
Route local traffic directly to reduce VPN traffic:
```json
{"domain_suffix": [".ru", ".рф"], "outbound": "direct"}
```

## Testing
```bash
curl -v --connect-timeout 5 https://37.1.212.51:443
openssl s_client -connect 37.1.212.51:443 -servername taxi.yandex.ru
```
