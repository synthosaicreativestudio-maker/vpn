#!/usr/bin/env python3
"""Собирает облегчённые geoip/geosite базы (PRIVATE + RU) из полных upstream-файлов.

Причина: iOS Network Extension (движок Happ/sing-box) ограничен по памяти
(~15-50 МБ в зависимости от версии iOS). Полные geoip.dat (~18 МБ, 260 стран)
и geosite.dat (~10 МБ, 1511 категорий) не влезают в этот лимит и роняют
VPN-модуль. Для сплит-туннелинга на iOS нужны только правила PRIVATE (RFC1918)
и RU (прямой доступ к российским сайтам) — этот скрипт вырезает только их.

Использование:
    python3 scripts/build_geo_light.py <geoip.dat> <geosite.dat> <output_dir>

Зависимости: protobuf (pip install protobuf), common_clean_pb2.py в этой же папке.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_clean_pb2 as pb

GEOIP_CODES = {"PRIVATE", "RU"}
GEOSITE_CODES = {"PRIVATE", "CATEGORY-RU"}


def build_geoip_light(src_path: str, dst_path: str) -> None:
    with open(src_path, "rb") as f:
        full = pb.GeoIPList()
        full.ParseFromString(f.read())

    light = pb.GeoIPList()
    for entry in full.entry:
        if entry.country_code.upper() in GEOIP_CODES:
            light.entry.append(entry)

    found = {e.country_code.upper() for e in light.entry}
    missing = GEOIP_CODES - found
    if missing:
        raise SystemExit(f"geoip: не найдены коды {missing} в {src_path}")

    with open(dst_path, "wb") as f:
        f.write(light.SerializeToString())
    print(f"geoip-light: {dst_path} ({os.path.getsize(dst_path)} байт, коды: {sorted(found)})")


def build_geosite_light(src_path: str, dst_path: str) -> None:
    with open(src_path, "rb") as f:
        full = pb.GeoSiteList()
        full.ParseFromString(f.read())

    light = pb.GeoSiteList()
    for entry in full.entry:
        if entry.country_code.upper() in GEOSITE_CODES:
            light.entry.append(entry)

    found = {e.country_code.upper() for e in light.entry}
    missing = GEOSITE_CODES - found
    if missing:
        raise SystemExit(f"geosite: не найдены коды {missing} в {src_path}")

    with open(dst_path, "wb") as f:
        f.write(light.SerializeToString())
    print(f"geosite-light: {dst_path} ({os.path.getsize(dst_path)} байт, коды: {sorted(found)})")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(1)
    geoip_src, geosite_src, out_dir = sys.argv[1:4]
    os.makedirs(out_dir, exist_ok=True)
    build_geoip_light(geoip_src, os.path.join(out_dir, "geoip-light.dat"))
    build_geosite_light(geosite_src, os.path.join(out_dir, "geosite-light.dat"))
