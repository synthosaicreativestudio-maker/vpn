import json
import base64
import qrcode
from pathlib import Path

DIR = Path("configs_2026_03_20")
ROOT = Path(".")

# 1. Read and update sub links
raw_sub_path = DIR / "raw_sub.txt"
if not raw_sub_path.exists():
    content = """vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:443?type=tcp&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&flow=xtls-rprx-vision#🚀-VLESS-Main
vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:8443?type=grpc&serviceName=taxi_grpc_service&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome#📡-VLESS-gRPC
hysteria2://HysteriaPassword2026@37.1.212.51:10443?sni=ya.ru&insecure=1#⚡-Hysteria2-Fast"""
    raw_sub_path.write_text(content)

content = raw_sub_path.read_text()
b64_sub = base64.b64encode(content.encode()).decode()
(DIR / "sub.txt").write_text(b64_sub)
(DIR / "sub_oneline.txt").write_text(b64_sub)

vless_main = content.splitlines()[0]

# 2. Generate QR for Amnezia (VLESS Link)
qr_am = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
qr_am.add_data(vless_main)
qr_am.make(fit=True)
img_am = qr_am.make_image(fill_color="black", back_color="white")
img_am.save(DIR / "qr_amnezia_vless.png")
print("Saved qr_amnezia_vless.png")

# 3. Generate QR for Hiddify (Full JSON Config)
hy_pack_path = DIR / "hy_pack.json"
if hy_pack_path.exists():
    hiddify_conf = json.loads(hy_pack_path.read_text())
    minified_hiddify = json.dumps(hiddify_conf, separators=(',', ':'))
    print(f"Hiddify JSON length: {len(minified_hiddify)} bytes")

    if len(minified_hiddify) <= 2900:
        qr_h = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=4, border=4)
        qr_h.add_data(minified_hiddify)
        qr_h.make(fit=True)
        img_h = qr_h.make_image(fill_color="black", back_color="white")
        img_h.save(DIR / "qr_hiddify.png")
        print("Saved qr_hiddify.png")
    else:
        print("JSON is too large for QR, creating QR with sub links instead.")
        qr_h = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=4)
        qr_h.add_data(content)
        qr_h.make(fit=True)
        img_h = qr_h.make_image(fill_color="black", back_color="white")
        img_h.save(DIR / "qr_hiddify.png")
        print("Saved qr_hiddify.png with direct links")
    
    # Also save as base64 for direct import if needed
    b64_h = base64.b64encode(minified_hiddify.encode()).decode()
    (DIR / "hiddify_config_b64.txt").write_text(b64_h)
else:
    print("Warning: hy_pack.json not found, skipping Hiddify QR")

