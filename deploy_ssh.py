import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print("Connecting to VPS...")
    ssh.connect('37.1.212.51', port=22, username='root', password='LEJ6U5chSK', timeout=10)
    
    # Check marzban dir
    stdin, stdout, stderr = ssh.exec_command('ls -l /var/lib/marzban/xray_config.json')
    res = stdout.read().decode().strip()
    
    target_path = None
    if 'xray_config.json' in res:
        target_path = '/var/lib/marzban/xray_config.json'
    else:
        stdin, stdout, stderr = ssh.exec_command('ls -l /opt/marzban/xray_config.json')
        res = stdout.read().decode().strip()
        if 'xray_config.json' in res:
            target_path = '/opt/marzban/xray_config.json'

    if not target_path:
        # Check standard location
        target_path = '/var/lib/marzban/xray_config.json'
    
    print(f"Deploying to {target_path}...")

    sftp = ssh.open_sftp()
    
    # Read local config
    local_conf = "configs_2026_03_20/xray_config_yandex.json"
    
    # Upload
    sftp.put(local_conf, target_path)
    sftp.close()
    
    print("Upload complete. Restarting Marzban...")
    
    # Restart marzban
    # Usually `marzban restart` works if it's installed via script, 
    # or `docker compose restart` in /opt/marzban
    stdin, stdout, stderr = ssh.exec_command('cd /opt/marzban && docker compose restart marzban')
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    if "no configuration file" in err.lower():
        stdin, stdout, stderr = ssh.exec_command('marzban restart')
        out = stdout.read().decode()
        err = stderr.read().decode()

    print("Restart STDOUT:", out)
    print("Restart STDERR:", err)

    ssh.close()
    print("Done!")
except Exception as e:
    print("Error:", str(e))
