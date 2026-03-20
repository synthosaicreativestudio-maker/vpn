import re
with open("_generate_qrs.py", "r") as f:
    text = f.read()

# Remove the Happ config part which was deleted
text = re.sub(r'# Generate QR for Happ.*?(?=\Z)', '', text, flags=re.DOTALL)

# Update raw_sub text generation for grpc
grpc_line = 'vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:8443?type=grpc&serviceName=taxi_grpc_service&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome#📡-VLESS-gRPC'
hysteria_line = 'hysteria2://HysteriaPassword2026@37.1.212.51:10443?sni=ya.ru&insecure=1#⚡-Hysteria2-Fast'
text = re.sub(r'vless://.*?sslip\.io.*?#📡-VLESS-XHTTP', grpc_line, text)
text = re.sub(r'hysteria2://.*?www\.microsoft\.com.*?#⚡-Hysteria2-Fast', hysteria_line, text)

# Just rebuild the content assignment carefully
replacement = """content = \"\"\"vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:443?type=tcp&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&flow=xtls-rprx-vision#🚀-VLESS-Main
vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:8443?type=grpc&serviceName=taxi_grpc_service&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome#📡-VLESS-gRPC
hysteria2://HysteriaPassword2026@37.1.212.51:10443?sni=ya.ru&insecure=1#⚡-Hysteria2-Fast\"\"\"
    raw_sub_path.write_text(content)"""

text = re.sub(r'content = """vless://.*?"""\n    raw_sub_path\.write_text\(content\)', replacement, text, flags=re.DOTALL)

with open("_generate_qrs.py", "w") as f:
    f.write(text)
