"""Генератор ссылок для всех VPN-протоколов.

Каждый метод формирует URI для конкретного протокола,
используя параметры из config.py.

Каналы (июль 2026) — Blue-Green параллельные ветки:
  Ветка 1 (Blue / основная):
    1. VLESS + Reality + Vision через Relay (TCP, порт 443)
    2. VLESS + Reality + gRPC через Relay   (H2, порт 2053)
    3. VLESS + Reality + Vision Direct      (TCP, порт 443)
  Ветка 2 (Green / резервная):
    4. VLESS + Reality + Vision через Relay (TCP, порт 10443)
    5. VLESS + Reality + gRPC через Relay   (H2, порт 12053)
    6. VLESS + Reality + Vision Direct      (TCP, порт 10443)
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
    PORT_VLESS_REALITY_2,
    REALITY_PUBLIC_KEY,
    REALITY_SHORT_ID,
    REALITY_SNI,
    RELAY_ENABLED,
    RELAY_GRPC_PORT_2,
    RELAY_IP,
    RELAY_PORT,
    RELAY_PORT_2,
    RELAY_PUBLIC_KEY,
    RELAY_SHORT_ID,
    RELAY_SNI,
    SERVER_IP,
    SHADOWSOCKS_METHOD,
    SHADOWSOCKS_PASSWORD,
    PORT_VLESS_WS,
    PORT_VLESS_XHTTP,
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
            + f"#{quote(f'🔌 {email} (Vision 1)')}"
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
    def vless_relay(email: str, uuid: str) -> str:
        """7. VLESS + Reality + Vision через Relay RU (обход БС ТСПУ).

        Использует РФ VPS как входную точку с whitelisted IP/SNI,
        трафик пробрасывается на US сервер.
        """
        return (
            f"vless://{uuid}@{RELAY_IP}:{RELAY_PORT}"
            f"?encryption=none&security=reality"
            f"&sni={RELAY_SNI}"
            f"&pbk={RELAY_PUBLIC_KEY}"
            f"&sid={RELAY_SHORT_ID}"
            f"&fp=chrome"
            f"&flow=xtls-rprx-vision"
            f"#{quote(f'📡 {email} (Relay RU 1)')}"
        )



    @staticmethod
    def vless_relay_xhttp(email: str, uuid: str) -> str:
        """10. VLESS + Reality + xHTTP через РФ-релей Яндекс ВМ (для МТС)."""
        return (
            f"vless://{uuid}@{RELAY_IP}:8443"
            f"?encryption=none&security=reality"
            f"&sni={RELAY_SNI}"
            f"&pbk={RELAY_PUBLIC_KEY}"
            f"&sid={RELAY_SHORT_ID}"
            f"&fp=chrome"
            f"&type=xhttp&mode=stream-up&path=/secretpath2026"
            f"#{quote(f'🕵️ {email} (xHTTP Relay RU new)')}"
        )

    @staticmethod
    def vless_relay_grpc(email: str, uuid: str) -> str:
        """11. VLESS + Reality + gRPC через РФ-релей Яндекс ВМ (для МТС)."""
        return (
            f"vless://{uuid}@{RELAY_IP}:2053"
            f"?encryption=none&security=reality"
            f"&sni={RELAY_SNI}"
            f"&pbk={RELAY_PUBLIC_KEY}"
            f"&sid={RELAY_SHORT_ID}"
            f"&fp=chrome"
            f"&type=grpc&serviceName=vpn-grpc"
            f"#{quote(f'📡 {email} (gRPC Relay RU 1)')}"
        )

    @staticmethod
    def hysteria2_relay(email: str) -> str:
        """12. Hysteria2 через РФ-релей Яндекс ВМ (для МТС)."""
        return (
            f"hysteria2://{HYSTERIA2_PASSWORD}@{RELAY_IP}:10443"
            f"?sni={RELAY_SNI}&insecure=1"
            f"&obfs=salamander&obfs-password={HYSTERIA2_OBFS_PASSWORD}"
            f"#{quote(f'🚀 {email} (Hysteria2 Relay RU)')}"
        )

    # ── Ветка 2 (Green / резервный канал) ─────────────────────────

    @classmethod
    def vless_reality_2(cls, uuid: str, email: str) -> str:
        """Ветка 2: VLESS + Reality + Vision (TCP, порт 10443) — прямой к US."""
        return (
            cls._vless_base(uuid, PORT_VLESS_REALITY_2)
            + "&flow=xtls-rprx-vision"
            + f"#{quote(f'🔌 {email} (Vision 2)')}"
        )

    @staticmethod
    def vless_relay_2(email: str, uuid: str) -> str:
        """Ветка 2: VLESS + Reality + Vision через Relay RU (порт 10443)."""
        return (
            f"vless://{uuid}@{RELAY_IP}:{RELAY_PORT_2}"
            f"?encryption=none&security=reality"
            f"&sni={RELAY_SNI}"
            f"&pbk={RELAY_PUBLIC_KEY}"
            f"&sid={RELAY_SHORT_ID}"
            f"&fp=chrome"
            f"&flow=xtls-rprx-vision"
            f"#{quote(f'📡 {email} (Relay RU 2)')}"
        )

    @staticmethod
    def vless_relay_grpc_2(email: str, uuid: str) -> str:
        """Ветка 2: VLESS + Reality + gRPC через Relay RU (порт 12053)."""
        return (
            f"vless://{uuid}@{RELAY_IP}:{RELAY_GRPC_PORT_2}"
            f"?encryption=none&security=reality"
            f"&sni={RELAY_SNI}"
            f"&pbk={RELAY_PUBLIC_KEY}"
            f"&sid={RELAY_SHORT_ID}"
            f"&fp=chrome"
            f"&type=grpc&serviceName=vpn-grpc"
            f"#{quote(f'📡 {email} (gRPC Relay RU 2)')}"
        )

    # ── Наборы ссылок ────────────────────────────────────────────

    @classmethod
    def _relay_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Relay-ссылки (через Яндекс ВМ) — приоритетные для мобильных операторов."""
        links: dict[str, str] = {}
        if RELAY_ENABLED:
            links["vless_relay"] = cls.vless_relay(email, uuid)
            links["vless_relay_xhttp"] = cls.vless_relay_xhttp(email, uuid)
            links["vless_relay_grpc"] = cls.vless_relay_grpc(email, uuid)
        return links

    @classmethod
    def _direct_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Прямые ссылки (к US серверу) — резервные для WiFi/стабильных сетей."""
        links = {
            "vless_reality": cls.vless_reality(uuid, email),
            "vless_xhttp": cls.vless_xhttp(uuid, email),
            "vless_grpc": cls.vless_grpc(uuid, email),
            "vless_ws": cls.vless_ws(uuid, email),
            "hysteria2": cls.hysteria2(email),
            "shadowsocks": cls.shadowsocks(email),
        }
        return links

    @classmethod
    def all_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Все каналы: только gRPC в обеих ветках."""
        links: dict[str, str] = {}
        # Ветка 1 (основная / Blue)
        if RELAY_ENABLED:
            links["vless_relay_grpc_1"] = cls.vless_relay_grpc(email, uuid)

        # Ветка 2 (резервная / Green)
        if RELAY_ENABLED:
            links["vless_relay_grpc_2"] = cls.vless_relay_grpc_2(email, uuid)
        return links

    @classmethod
    def hiddify_links(cls, uuid: str, email: str, routing: str = None) -> dict[str, str]:
        """Только gRPC в обеих ветках для Hiddify."""
        links: dict[str, str] = {}
        # Ветка 1 (основная / Blue)
        if RELAY_ENABLED:
            links["vless_relay_grpc_1"] = cls.vless_relay_grpc(email, uuid)

        # Ветка 2 (резервная / Green)
        if RELAY_ENABLED:
            links["vless_relay_grpc_2"] = cls.vless_relay_grpc_2(email, uuid)
        return links

    @classmethod
    def happ_links(cls, uuid: str, email: str, routing: str = None) -> dict[str, str]:
        """Каналы для Happ (iOS): только gRPC в обеих ветках (Blue-Green)."""
        links: dict[str, str] = {}
        # Ветка 1 (основная / Blue)
        if RELAY_ENABLED:
            links["vless_relay_grpc_1"] = cls.vless_relay_grpc(email, uuid)
        # Ветка 2 (резервная / Green)
        if RELAY_ENABLED:
            links["vless_relay_grpc_2"] = cls.vless_relay_grpc_2(email, uuid)
        return links

    @classmethod
    def happ_test_links(cls, uuid: str, email: str, routing: str = None) -> dict[str, str]:
        """Ссылки для тестирования в Happ (только стабильные + тестовый DNS профиль)."""
        links: dict[str, str] = {}
        # Стандартные стабильные ссылки Happ для сравнения и тестирования DNS
        links.update(cls.happ_links(uuid, email, routing))
        return links

    # ── Текст подписок ───────────────────────────────────────────

    @classmethod
    def subscription_text(cls, uuid: str, email: str) -> str:
        """Текст подписки — все ссылки (универсальный)."""
        links = cls.all_links(uuid, email)
        return "\n".join(links.values())

    @classmethod
    def subscription_text_hiddify(cls, uuid: str, email: str, routing: str = None) -> str:
        """Текст подписки оптимизированный для Hiddify."""
        links = cls.hiddify_links(uuid, email, routing)
        return "\n".join(links.values())

    @classmethod
    def subscription_text_happ(cls, uuid: str, email: str, routing: str = None) -> str:
        """Текст подписки оптимизированный для Happ."""
        links = cls.happ_links(uuid, email, routing)
        return "\n".join(links.values())

    @classmethod
    def subscription_text_happ_test(cls, uuid: str, email: str, routing: str = None) -> str:
        """Текст подписки для Happ с тестовыми xHTTP протоколами."""
        links = cls.happ_test_links(uuid, email, routing)
        return "\n".join(links.values())

