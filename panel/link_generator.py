"""Генератор ссылок для всех VPN-протоколов.

Каждый метод формирует URI для конкретного протокола,
используя параметры из config.py.

Каналы (март 2026):
  1. VLESS + Reality + Vision  (TCP, порт 443)
  2. VLESS + Reality + xHTTP   (xHTTP stream-up, порт 8443)
  3. VLESS + Reality + gRPC    (H2, порт 2053)
  4. VLESS + Reality + WS      (WebSocket, порт 2083)
  5. Hysteria2                 (UDP/QUIC, порт 10443)
  6. Yandex Bridge xHTTP       (через Yandex VM, порт 8880)
  7. Yandex Bridge WS          (через Yandex VM, порт 8881)
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
    PORT_YANDEX_BRIDGE,
    PORT_YANDEX_BRIDGE_WS,
    REALITY_PUBLIC_KEY,
    REALITY_SHORT_ID,
    REALITY_SNI,
    SERVER_IP,
    YANDEX_BRIDGE_HOST,
    YANDEX_BRIDGE_PATH,
    YANDEX_BRIDGE_WS_PATH,
    YANDEX_VM_IP,
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
        """5. Hysteria2 (UDP/QUIC, порт 10443)."""
        return (
            f"hysteria2://{HYSTERIA2_PASSWORD}@{SERVER_IP}:{PORT_HYSTERIA2}"
            f"?sni={HYSTERIA2_SNI}&insecure=1"
            f"#{quote(f'🚀 {email} (Hysteria2)')}"
        )

    @classmethod
    def yandex_bridge_xhttp(cls, uuid: str, email: str) -> str:
        """6. Yandex Bridge xHTTP (через Yandex VM, порт 8880)."""
        return (
            f"vless://{uuid}@{YANDEX_VM_IP}:{PORT_YANDEX_BRIDGE}"
            f"?encryption=none&security=none"
            f"&type=xhttp"
            f"&host={YANDEX_BRIDGE_HOST}"
            f"&path={YANDEX_BRIDGE_PATH}"
            f"#{quote(f'🌉 {email} (Yandex Bridge)')}"
        )

    @classmethod
    def yandex_bridge_ws(cls, uuid: str, email: str) -> str:
        """7. Yandex Bridge WebSocket (через Yandex VM, порт 8881)."""
        return (
            f"vless://{uuid}@{YANDEX_VM_IP}:{PORT_YANDEX_BRIDGE_WS}"
            f"?encryption=none&security=none"
            f"&type=ws"
            f"&host={YANDEX_BRIDGE_HOST}"
            f"&path={YANDEX_BRIDGE_WS_PATH}"
            f"#{quote(f'🌉 {email} (YaBridge WS)')}"
        )

    # ── Наборы ссылок ────────────────────────────────────────────

    @classmethod
    def all_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Все ссылки для пользователя (7 каналов)."""
        return {
            "vless_reality": cls.vless_reality(uuid, email),
            "vless_xhttp": cls.vless_xhttp(uuid, email),
            "vless_grpc": cls.vless_grpc(uuid, email),
            "vless_ws": cls.vless_ws(uuid, email),
            "hysteria2": cls.hysteria2(email),
            "yandex_bridge": cls.yandex_bridge_xhttp(uuid, email),
            "yandex_bridge_ws": cls.yandex_bridge_ws(uuid, email),
        }

    @classmethod
    def hiddify_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Ссылки оптимизированные для Hiddify.

        Hiddify поддерживает все протоколы включая gRPC и Hysteria2.
        """
        return {
            "vless_reality": cls.vless_reality(uuid, email),
            "vless_xhttp": cls.vless_xhttp(uuid, email),
            "vless_grpc": cls.vless_grpc(uuid, email),
            "vless_ws": cls.vless_ws(uuid, email),
            "hysteria2": cls.hysteria2(email),
            "yandex_bridge": cls.yandex_bridge_xhttp(uuid, email),
            "yandex_bridge_ws": cls.yandex_bridge_ws(uuid, email),
        }

    @classmethod
    def happ_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Ссылки оптимизированные для Happ (Sing-Box).

        Happ НЕ поддерживает gRPC.
        Hysteria2 может работать нестабильно — оставляем для тестов.
        """
        return {
            "vless_reality": cls.vless_reality(uuid, email),
            "vless_xhttp": cls.vless_xhttp(uuid, email),
            "vless_ws": cls.vless_ws(uuid, email),
            "hysteria2": cls.hysteria2(email),
            "yandex_bridge": cls.yandex_bridge_xhttp(uuid, email),
            "yandex_bridge_ws": cls.yandex_bridge_ws(uuid, email),
        }

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
