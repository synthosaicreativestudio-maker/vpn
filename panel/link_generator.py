"""Генератор ссылок для всех VPN-протоколов.

Каждый метод формирует URI для конкретного протокола,
используя параметры из config.py.

Каналы (май 2026):
  1. VLESS + Reality + Vision  (TCP, порт 443)
  2. VLESS + Reality + xHTTP   (xHTTP stream-one, порт 8443) — только Xray-клиенты
  3. VLESS + Reality + gRPC    (H2, порт 2053)
  4. VLESS + Reality + WS      (WebSocket, порт 2083)
  5. Hysteria2 + Salamander    (UDP/QUIC, порт 10443, obfs)
  6. Shadowsocks 2022          (TCP+UDP, порт 2085)
"""

from urllib.parse import quote

from panel.config import (
    HYSTERIA2_OBFS_PASSWORD,
    HYSTERIA2_PASSWORD,
    HYSTERIA2_SNI,
    PORT_HYSTERIA2,
    PORT_SHADOWSOCKS,
    PORT_VLESS_GRPC,
    PORT_VLESS_REALITY,
    PORT_VLESS_WS,
    PORT_VLESS_XHTTP,
    REALITY_PUBLIC_KEY,
    REALITY_SHORT_ID,
    REALITY_SNI,
    RELAY_ENABLED,
    RELAY_IP,
    RELAY_PORT,
    RELAY_PUBLIC_KEY,
    RELAY_SHORT_ID,
    RELAY_SNI,
    RELAY_UUID,
    SERVER_IP,
    SHADOWSOCKS_METHOD,
    SHADOWSOCKS_PASSWORD,
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
        return (
            f"vless://{uuid}@{SERVER_IP}:{PORT_VLESS_WS}"
            f"?encryption=none&security=none&type=ws&path=/ws-tunnel"
            + f"#{quote(f'🌐 {email} (WebSocket)')}"
        )

    @staticmethod
    def hysteria2(email: str) -> str:
        """5. Hysteria2 + Salamander obfs (UDP/QUIC, порт 10443)."""
        return (
            f"hysteria2://{HYSTERIA2_PASSWORD}@{SERVER_IP}:{PORT_HYSTERIA2}"
            f"?sni={HYSTERIA2_SNI}&insecure=1"
            f"&obfs=salamander&obfs-password={HYSTERIA2_OBFS_PASSWORD}"
            f"#{quote(f'🚀 {email} (Hysteria2)')}"
        )

    @staticmethod
    def shadowsocks(email: str) -> str:
        """6. Shadowsocks 2022 (TCP+UDP, порт 2085)."""
        import base64

        # SS URI: ss://method:password@host:port#fragment
        userinfo = base64.urlsafe_b64encode(
            f"{SHADOWSOCKS_METHOD}:{SHADOWSOCKS_PASSWORD}".encode()
        ).decode().rstrip("=")
        return (
            f"ss://{userinfo}@{SERVER_IP}:{PORT_SHADOWSOCKS}"
            f"#{quote(f'🔒 {email} (Shadowsocks)')}"
        )

    @staticmethod
    def vless_relay(email: str) -> str:
        """7. VLESS + Reality + Vision через Relay RU (обход БС ТСПУ).

        Использует РФ VPS как входную точку с whitelisted IP/SNI,
        трафик пробрасывается на US сервер.
        UUID фиксированный (relay-пользователь, не персональный).
        """
        return (
            f"vless://{RELAY_UUID}@{RELAY_IP}:{RELAY_PORT}"
            f"?encryption=none&security=reality"
            f"&sni={RELAY_SNI}"
            f"&pbk={RELAY_PUBLIC_KEY}"
            f"&sid={RELAY_SHORT_ID}"
            f"&fp=chrome"
            f"&flow=xtls-rprx-vision"
            f"#{quote(f'📡 {email} (Relay RU)')}"
        )

    # ── Наборы ссылок ────────────────────────────────────────────

    @classmethod
    def all_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Vision (US напрямую) + Relay RU (обход БС)."""
        links = {
            "vless_reality": cls.vless_reality(uuid, email),
        }
        if RELAY_ENABLED:
            links["vless_relay"] = cls.vless_relay(email)
        return links

    @classmethod
    def hiddify_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Vision + Relay RU."""
        links = {
            "vless_reality": cls.vless_reality(uuid, email),
        }
        if RELAY_ENABLED:
            links["vless_relay"] = cls.vless_relay(email)
        return links

    @classmethod
    def happ_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Vision + Relay RU."""
        links = {
            "vless_reality": cls.vless_reality(uuid, email),
        }
        if RELAY_ENABLED:
            links["vless_relay"] = cls.vless_relay(email)
        return links

    # ── Текст подписок ───────────────────────────────────────────

    @classmethod
    def subscription_text(cls, uuid: str, email: str) -> str:
        """Текст подписки — все ссылки (универсальный)."""
        links = cls.all_links(uuid, email)
        return "\n".join(links.values())

    @classmethod
    def subscription_text_hiddify(cls, uuid: str, email: str) -> str:
        """Текст подписки оптимизированный для Hiddify."""
        links = cls.hiddify_links(uuid, email)
        return "\n".join(links.values())

    @classmethod
    def subscription_text_happ(cls, uuid: str, email: str) -> str:
        """Текст подписки оптимизированный для Happ."""
        links = cls.happ_links(uuid, email)
        return "\n".join(links.values())
