---
name: OSINT & Reconnaissance
description: Open Source Intelligence, leak detection, IP/DNS analysis
version: 1.0.0
---

# OSINT & Reconnaissance

## IP & Network Intelligence

### Check Your Own Exposure
```bash
# What IP is visible
curl https://ip-api.com/json | jq
curl https://ifconfig.me
curl https://ipinfo.io

# DNS leak test
curl https://ipleak.net/json/

# Full leak test (browser required)
# https://ipleak.net
# https://browserleaks.com/ip
# https://whoer.net
```

### Analyze Target IP
```bash
# IP geolocation and ISP
curl "https://ip-api.com/json/37.1.212.51?fields=status,country,city,isp,org,as"

# WHOIS lookup
whois 37.1.212.51

# Reverse DNS
dig -x 37.1.212.51

# Shodan (requires API key)
shodan host 37.1.212.51
```

### Port & Service Discovery
```bash
# Quick scan
nmap -F 37.1.212.51

# Aggressive scan (use only on owned servers)
nmap -A -T4 37.1.212.51

# Check specific ports
nmap -p 443,8080,22 37.1.212.51

# Service version detection
nmap -sV -p 443 37.1.212.51
```

## Leak Detection

### Common VPN Leaks

| Leak Type | Detection | Prevention |
|-----------|-----------|------------|
| **IP Leak** | ipleak.net shows real IP | Enable kill switch |
| **DNS Leak** | DNS requests bypass VPN | Force VPN DNS servers |
| **WebRTC Leak** | Browser exposes local IP | Disable WebRTC |
| **IPv6 Leak** | IPv6 not routed through VPN | Disable IPv6 or route it |

### Check If VPN Is Working
```bash
# Before VPN
curl https://ip-api.com/json | jq '.query, .country'

# After VPN
curl https://ip-api.com/json | jq '.query, .country'

# Should show VPN server IP and country
```

## Domain & Certificate Intelligence

```bash
# SSL certificate info
echo | openssl s_client -connect 37.1.212.51:443 2>/dev/null | openssl x509 -noout -text

# Certificate transparency logs
# https://crt.sh/?q=domain.com

# DNS records
dig ANY domain.com

# Subdomain enumeration
subfinder -d domain.com
```

## Social Engineering & OSINT Tools

### Online Resources
- **Shodan.io** - Search engine for IoT and servers
- **Censys.io** - Internet-wide scan data
- **Hunter.io** - Email finder
- **Have I Been Pwned** - Breach database
- **VirusTotal** - File/URL/IP analysis

### Browser Extensions for OSINT
- Wappalyzer - Identify web technologies
- BuiltWith - Technology profiler
- IP Address and Domain Information

## Server Exposure Check

```bash
# What's exposed on your VPN server
nmap -sT -O 37.1.212.51

# Check for common vulnerabilities
nmap --script vuln 37.1.212.51

# SSL/TLS analysis
testssl.sh 37.1.212.51:443
```

## Instructions
- Regularly check for IP/DNS leaks after VPN config changes
- Minimize open ports on VPN server (only 443, 22)
- Use Shodan to see how your server appears to attackers
- Verify WebRTC is disabled in browsers for privacy
