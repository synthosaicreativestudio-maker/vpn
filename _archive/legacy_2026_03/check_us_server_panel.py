import paramiko

def run_diagnostic():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('37.1.212.51', port=22, username='root', password='LEJ6U5chSK', timeout=10)
        
        commands = [
            "echo '--- STATUS ---'",
            "systemctl is-active xray caddy panel bot || true",
            "systemctl status panel --no-pager || true",
            "echo '--- FILES IN /opt/ ---'",
            "ls -la /opt/ || true",
            "echo '--- LOGS ---'",
            "journalctl -u panel -n 50 --no-pager || true"
        ]
        
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            if out:
                print(out)
            if err:
                print("STDERR:", err)
        
        ssh.close()
    except Exception as e:
        print("Paramiko Error:", str(e))

if __name__ == '__main__':
    run_diagnostic()
