---
name: Network Diagnostics  
description: Network analysis, packet capture, connection troubleshooting
version: 1.0.0
---

# Network Diagnostics

## Core Skills

### Port & Service Analysis
```bash
# Check listening ports
ss -tlnp                     # TCP listening
ss -ulnp                     # UDP listening
netstat -tlnp | grep LISTEN

# Check specific port
lsof -i :443
nc -zv server.com 443

# Check all connections
ss -s                        # Summary
ss -tunapl                   # All connections with processes
```

### DNS Diagnostics
```bash
# DNS resolution
dig example.com
nslookup example.com
host example.com

# Check DNS leaks (what DNS server is used)
dig +short myip.opendns.com @resolver1.opendns.com

# Flush DNS cache
# macOS
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
# Linux
sudo systemd-resolve --flush-caches
```

### Traffic Analysis
```bash
# Capture packets on interface
sudo tcpdump -i eth0 port 443 -w capture.pcap

# Filter by host
sudo tcpdump host 37.1.212.51

# Show HTTP requests
sudo tcpdump -A -s0 port 80

# Detailed packet analysis
tshark -r capture.pcap -Y "tls.handshake"
```

### Connection Testing
```bash
# HTTP/HTTPS check
curl -v https://example.com
curl -x socks5://127.0.0.1:1080 https://ip-api.com

# Trace route
traceroute example.com
mtr example.com          # Real-time traceroute

# Speed test
curl -o /dev/null -w "Speed: %{speed_download}\n" https://example.com/file
```

### Firewall (UFW/iptables)
```bash
# UFW status
ufw status verbose
ufw allow 443/tcp
ufw delete allow 8080/tcp

# iptables
iptables -L -n -v
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

### VPN-Specific Diagnostics
```bash
# Check TUN interface
ip addr show tun0
ifconfig utun0  # macOS

# Check routing table
ip route show
netstat -rn

# Check if traffic goes through VPN
curl https://ip-api.com/json
curl https://ipleak.net/json/

# WebRTC leak test
# Only possible in browser - use ipleak.net
```

## Common Issues

| Problem | Diagnostic Command | Solution |
|---------|-------------------|----------|
| Port blocked | `nc -zv host 443` | Check firewall, use different port |
| DNS leak | Check ipleak.net | Configure DNS in VPN client |
| Slow connection | `mtr host` | Check packet loss, change server |
| TLS error | `openssl s_client -connect host:443` | Check certificates, SNI |

## Instructions
- Always check basic connectivity first (ping, port)
- Verify DNS resolution before deeper analysis
- Use tcpdump sparingly - can generate large files
- Check both client and server-side when troubleshooting
