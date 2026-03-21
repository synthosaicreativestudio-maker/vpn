"""Генератор ссылок для всех VPN-протоколов.

Каждый метод формирует URI для конкретного протокола,
используя параметры из config.py.

Каналы (март 2026):
  1. VLESS + Reality + Vision  (TCP, порт 443)
  2. VLESS + Reality + xHTTP   (xHTTP stream-up, порт 8443)
  3. VLESS + Reality + gRPC    (H2, порт 2053)
  4. VLESS + Reality + WS      (WebSocket, порт 2083)
  5. Hysteria2                 (UDP/QUIC, порт 10443)
"""

from urllib.parse import quote

from panel.config import (
    HYSTERIA2_PASSWORD,
    HYSTERIA2_SNI,
    PORT_HYSTERIA2,
    PORT_VLESS_GRPC,
    PORT_VLESS_REALITY,
    PORT_VLESS_WS,
    PORT_VLESS_XHTTP,
    REALITY_PUBLIC_KEY,
    REALITY_SHORT_ID,
    REALITY_SNI,
    SERVER_IP,
)


class LinkGenerator:
    """Генератор ссылок подключения для всех активных протоколов."""

    @staticmethod
    def _vless_base(uuid: str, port: int) -> str:
        """Базовая часть VLESS + Reality URI."""
        return (
            f"vless://{uuid}@{SERVER_IP}:{port}"
            f"?encryption=none&security=reality"
            f"&sni={REALITY_SNI}"
            f"&pbk={REALITY_PUBLIC_KEY}"
            f"&sid={REALITY_SHORT_ID}"
            f"&fp=chrome"
        )

    @classmethod
    def vless_reality(cls, uuid: str, email: str) -> str:
        """1. VLESS + Reality + Vision (TCP, порт 443)."""
        return (
            cls._vless_base(uuid, PORT_VLESS_REALITY)
            + "&flow=xtls-rprx-vision"
            + f"#{quote(f'🔌 {email} (Vision)')}"
        )

    @classmethod
    def vless_xhttp(cls, uuid: str, email: str) -> str:
        """2. VLESS + Reality + xHTTP stream-up (порт 8443)."""
        return (
            cls._vless_base(uuid, PORT_VLESS_XHTTP)
            + "&type=xhttp&mode=stream-up&path=/secretpath2026"
            + f"#{quote(f'🕵️ {email} (xHTTP)')}"
        )

    @classmethod
    def vless_grpc(cls, uuid: str, email: str) -> str:
        """3. VLESS + Reality + gRPC (порт 2053)."""
        return (
            cls._vless_base(uuid, PORT_VLESS_GRPC)
            + "&type=grpc&serviceName=vpn-grpc"
            + f"#{quote(f'📡 {email} (gRPC)')}"
        )

    @classmethod
    def vless_ws(cls, uuid: str, email: str) -> str:
        """4. VLESS + Reality + WebSocket (порт 2083)."""
        # WebSocket на этом сервере теперь без Reality для стабильности
        return (
            f"vless://{uuid}@{SERVER_IP}:{PORT_VLESS_WS}"
            f"?encryption=none&security=none&type=ws&path=/ws-tunnel"
            + f"#{quote(f'🌐 {email} (WebSocket)')}"
        )

    @staticmethod
    def hysteria2(email: str) -> str:
        """5. Hysteria2 (UDP/QUIC, порт 10443)."""
        return (
            f"hysteria2://{HYSTERIA2_PASSWORD}@{SERVER_IP}:{PORT_HYSTERIA2}"
            f"?sni={HYSTERIA2_SNI}&insecure=1"
            f"#{quote(f'🚀 {email} (Hysteria2)')}"
        )

    @classmethod
    def all_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Все ссылки для пользователя (5 каналов)."""
        return {
            "vless_reality": cls.vless_reality(uuid, email),
            "vless_xhttp": cls.vless_xhttp(uuid, email),
            "vless_grpc": cls.vless_grpc(uuid, email),
            "vless_ws": cls.vless_ws(uuid, email),
            "hysteria2": cls.hysteria2(email),
        }

    @classmethod
    def subscription_text(cls, uuid: str, email: str) -> str:
        """Текст подписки (все ссылки через перенос строки)."""
        links = cls.all_links(uuid, email)
        return "\n".join(links.values())
