---
name: Network Diagnostics  
description: Network analysis, packet capture, connection troubleshooting
version: 1.0.0
---

# Network Diagnostics

## Port & Service Analysis
```bash
ss -tlnp                     # TCP listening
ss -ulnp                     # UDP listening
lsof -i :443                 # Check specific port
nc -zv server.com 443        # Test connection
```

## DNS Diagnostics
```bash
dig example.com
nslookup example.com
# Flush DNS (macOS)
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
```

## Traffic Analysis
```bash
sudo tcpdump -i eth0 port 443 -w capture.pcap
sudo tcpdump host 37.1.212.51
tshark -r capture.pcap -Y "tls.handshake"
```

## Firewall (UFW)
```bash
ufw status verbose
ufw allow 443/tcp
ufw delete allow 8080/tcp
```

## VPN-Specific
```bash
ip addr show tun0            # Check TUN interface
ip route show                # Routing table
curl https://ip-api.com/json # Check visible IP
```

## Common Issues

| Problem | Command | Solution |
|---------|---------|----------|
| Port blocked | `nc -zv host 443` | Check firewall |
| DNS leak | ipleak.net | Configure DNS |
| Slow connection | `mtr host` | Check packet loss |
| TLS error | `openssl s_client -connect host:443` | Check SNI |
