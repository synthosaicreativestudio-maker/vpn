import json
import base64
import qrcode
from pathlib import Path

DIR = Path("configs_2026_03_20")
ROOT = Path(".")

# 1. Read and update raw_sub.txt
raw_sub_path = DIR / "raw_sub.txt"
if raw_sub_path.exists():
    content = raw_sub_path.read_text()
    if 'sni=www.microsoft.com' in content:
        content = content.replace('sni=www.microsoft.com', 'sni=taxi.yandex.ru')
        raw_sub_path.write_text(content)
        # Update sub.txt
        b64 = base64.b64encode(content.encode()).decode()
        (DIR / "sub.txt").write_text(b64)
        (DIR / "sub_oneline.txt").write_text(b64)
else:
    content = """vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:443?type=tcp&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&flow=xtls-rprx-vision#🚀-VLESS-Main
vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:8443?type=grpc&serviceName=taxi_grpc_service&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome#📡-VLESS-gRPC
hysteria2://HysteriaPassword2026@37.1.212.51:10443?sni=ya.ru&insecure=1#⚡-Hysteria2-Fast"""
    raw_sub_path.write_text(content)
    b64 = base64.b64encode(content.encode()).decode()
    (DIR / "sub.txt").write_text(b64)
    (DIR / "sub_oneline.txt").write_text(b64)

vless_main = content.splitlines()[0]

# Generate QR for Amnezia
qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
qr.add_data(vless_main)
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white")
img.save(DIR / "qr_amnezia_vless.png")
print("Saved qr_amnezia_vless.png")

# Generate QR for Hiddify
hiddify_conf = json.loads((DIR / "hiddify_ALL_IN_ONE.json").read_text())
minified_hiddify = json.dumps(hiddify_conf, separators=(',', ':'))
print(f"Hiddify length: {len(minified_hiddify)} bytes")

qr_h = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=4, border=4)
qr_h.add_data(minified_hiddify)
qr_h.make(fit=True)
img_h = qr_h.make_image(fill_color="black", back_color="white")
img_h.save(DIR / "qr_hiddify.png")
print("Saved qr_hiddify.png")

