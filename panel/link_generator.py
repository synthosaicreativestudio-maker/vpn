"""Генератор ссылок для всех VPN-протоколов.

Каждый метод формирует URI для конкретного протокола,
используя параметры из config.py.
"""

from urllib.parse import quote

from panel.config import (
    PORT_HYSTERIA2,
    PORT_SHADOW_TLS,
    PORT_TUIC,
    PORT_VLESS_GRPC,
    PORT_VLESS_REALITY,
    PORT_VLESS_XHTTP,
    REALITY_PUBLIC_KEY,
    REALITY_SNI,
    SERVER_IP,
    SHADOW_TLS_PASSWORD,
)


class LinkGenerator:
    """Генератор ссылок подключения для всех активных протоколов."""

    @staticmethod
    def vless_reality(uuid: str, email: str) -> str:
        """VLESS + Reality + Vision (TCP, порт 10443)."""
        return (
            f"vless://{uuid}@{SERVER_IP}:{PORT_VLESS_REALITY}"
            f"?encryption=none&security=reality"
            f"&sni={REALITY_SNI}"
            f"&pbk={REALITY_PUBLIC_KEY}"
            f"&fp=chrome&flow=xtls-rprx-vision"
            f"#{quote(f'🔌 {email} (Direct)')}"
        )

    @staticmethod
    def vless_xhttp(uuid: str, email: str) -> str:
        """VLESS + Reality + xHTTP (TCP, порт 10444)."""
        return (
            f"vless://{uuid}@{SERVER_IP}:{PORT_VLESS_XHTTP}"
            f"?encryption=none&security=reality"
            f"&sni={REALITY_SNI}"
            f"&pbk={REALITY_PUBLIC_KEY}"
            f"&fp=chrome&type=xhttp&mode=packet-up&path=/secretpath2026"
            f"#{quote(f'🕵️ {email} (xHTTP)')}"
        )

    @staticmethod
    def vless_grpc(uuid: str, email: str) -> str:
        """VLESS + Reality + gRPC (TCP, порт 18443)."""
        return (
            f"vless://{uuid}@{SERVER_IP}:{PORT_VLESS_GRPC}"
            f"?encryption=none&security=reality"
            f"&sni={REALITY_SNI}"
            f"&pbk={REALITY_PUBLIC_KEY}"
            f"&fp=chrome&type=grpc&serviceName=grpc"
            f"#{quote(f'📡 {email} (gRPC)')}"
        )

    @staticmethod
    def shadow_tls(email: str) -> str:
        """Shadow-TLS v3 (TCP, порт 443)."""
        return (
            f"shadow-tls://{SHADOW_TLS_PASSWORD}@{SERVER_IP}:{PORT_SHADOW_TLS}"
            f"?sni={REALITY_SNI}&version=3"
            f"#{quote(f'🔐 {email} (ShadowTLS)')}"
        )

    @staticmethod
    def tuic(uuid: str, email: str) -> str:
        """TUIC v5 (UDP, порт 30445)."""
        return (
            f"tuic://{uuid}:{uuid}@{SERVER_IP}:{PORT_TUIC}"
            f"?congestion_control=bbr&sni={REALITY_SNI}&alpn=h3&insecure=1"
            f"#{quote(f'⚡ {email} (TUIC)')}"
        )

    @staticmethod
    def hysteria2(email: str) -> str:
        """Hysteria2 (UDP/QUIC, порт 10443)."""
        return (
            f"hysteria2://HysteriaPassword2026@{SERVER_IP}:{PORT_HYSTERIA2}"
            f"?sni=www.microsoft.com&insecure=1"
            f"#{quote(f'🚀 {email} (Hysteria2)')}"
        )

    @classmethod
    def all_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Все ссылки для пользователя."""
        return {
            "vless_reality": cls.vless_reality(uuid, email),
            "vless_xhttp": cls.vless_xhttp(uuid, email),
            "vless_grpc": cls.vless_grpc(uuid, email),
            "shadow_tls": cls.shadow_tls(email),
            "tuic": cls.tuic(uuid, email),
            "hysteria2": cls.hysteria2(email),
        }

    @classmethod
    def subscription_text(cls, uuid: str, email: str) -> str:
        """Текст подписки (все ссылки через перенос строки)."""
        links = cls.all_links(uuid, email)
        return "\n".join(links.values())
