---
name: Server Security & Hardening
description: Linux server security, firewalls, fail2ban, SSH hardening
version: 1.0.0
---

# Server Security & Hardening

## SSH Hardening

### Secure SSH Config
```bash
# /etc/ssh/sshd_config
Port 22                          # Consider changing to non-standard
PermitRootLogin prohibit-password  # Key-only for root
PasswordAuthentication no        # Disable password auth
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers root                  # Whitelist users

# Apply changes
sudo systemctl restart sshd
```

### SSH Key Setup
```bash
# Generate key (on client)
ssh-keygen -t ed25519 -C "vpn-server"

# Copy to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@37.1.212.51

# Test connection
ssh -i ~/.ssh/id_ed25519 root@37.1.212.51
```

## Firewall Configuration

### UFW (Recommended for Ubuntu)
```bash
# Enable UFW
ufw enable

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow essential ports
ufw allow 22/tcp      # SSH
ufw allow 443/tcp     # VLESS/HTTPS
ufw allow 8080/tcp    # TinyProxy (if needed)

# Check status
ufw status verbose

# Deny specific IP
ufw deny from 1.2.3.4

# Rate limiting for SSH
ufw limit 22/tcp
```

### iptables (Advanced)
```bash
# Drop invalid packets
iptables -A INPUT -m state --state INVALID -j DROP

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow specific ports
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Drop everything else
iptables -A INPUT -j DROP

# Save rules
iptables-save > /etc/iptables.rules
```

## Fail2ban Setup

```bash
# Install
apt install fail2ban

# Configure SSH protection
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 24h
EOF

# Start and enable
systemctl enable fail2ban
systemctl start fail2ban

# Check banned IPs
fail2ban-client status sshd
```

## System Hardening

### Disable Unnecessary Services
```bash
# List running services
systemctl list-units --type=service --state=running

# Disable unused services
systemctl disable --now postfix
systemctl disable --now snapd
```

### Automatic Updates
```bash
# Ubuntu/Debian
apt install unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades

# Enable security updates only
echo 'Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};' > /etc/apt/apt.conf.d/50unattended-upgrades
```

### Kernel Hardening
```bash
# /etc/sysctl.conf
net.ipv4.tcp_syncookies = 1          # SYN flood protection
net.ipv4.conf.all.rp_filter = 1      # Reverse path filtering
net.ipv4.conf.default.rp_filter = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0

# Apply
sysctl -p
```

## Docker Security

```bash
# Run containers as non-root
docker run --user 1000:1000 ...

# Limit resources
docker run --memory=512m --cpus=1 ...

# Read-only filesystem
docker run --read-only ...

# No new privileges
docker run --security-opt=no-new-privileges ...
```

## Security Audit Checklist

- [ ] SSH: Key-only auth, no root password
- [ ] Firewall: Only necessary ports open
- [ ] Fail2ban: Active and monitoring
- [ ] Updates: Automatic security updates enabled
- [ ] Docker: Containers running as non-root
- [ ] Logs: Centralized logging configured
- [ ] Backups: Regular automated backups

## Monitoring Commands
```bash
# Check login attempts
grep "Failed password" /var/log/auth.log | tail -20

# Current connections
ss -tunapl

# Resource usage
htop
df -h
free -h

# Docker containers
docker ps
docker stats
```

## Instructions
- Always use SSH keys, never passwords
- Keep firewall rules minimal (deny by default)
- Enable fail2ban for all exposed services
- Regularly update system and Docker images
- Monitor logs for suspicious activity
