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
    ANTI_STUB_FP,
    ANTI_STUB_IP,
    ANTI_STUB_PORT,
    ANTI_STUB_SNI,
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

    @classmethod
    def vless_ws_cdn(cls, uuid: str, email: str) -> str:
        """4a. VLESS + WebSocket + TLS через Cloudflare CDN (порт 443)."""
        from panel.config import CLOUDFLARE_CDN_DOMAIN
        return (
            f"vless://{uuid}@{CLOUDFLARE_CDN_DOMAIN}:443"
            f"?encryption=none&security=tls&tls=1&type=ws&host={CLOUDFLARE_CDN_DOMAIN}&sni={CLOUDFLARE_CDN_DOMAIN}&path=/ws-tunnel"
            + f"#{quote(f'☁️ {email} (CDN WebSocket TLS)')}"
        )

    @classmethod
    def vless_ws_cdn_plain(cls, uuid: str, email: str) -> str:
        """4b. VLESS + WebSocket через Cloudflare CDN без TLS (порт 80)."""
        from panel.config import CLOUDFLARE_CDN_DOMAIN
        return (
            f"vless://{uuid}@{CLOUDFLARE_CDN_DOMAIN}:80"
            f"?encryption=none&security=none&type=ws&host={CLOUDFLARE_CDN_DOMAIN}&path=/ws-tunnel"
            + f"#{quote(f'☁️ {email} (CDN WebSocket Plain)')}"
        )

    @classmethod
    def vless_grpc_cdn(cls, uuid: str, email: str) -> str:
        """4c. VLESS + gRPC + TLS через Cloudflare CDN (порт 443)."""
        from panel.config import CLOUDFLARE_CDN_DOMAIN
        return (
            f"vless://{uuid}@{CLOUDFLARE_CDN_DOMAIN}:443"
            f"?encryption=none&security=tls&tls=1&type=grpc&host={CLOUDFLARE_CDN_DOMAIN}&sni={CLOUDFLARE_CDN_DOMAIN}&serviceName=grpc"
            + f"#{quote(f'☁️ {email} (CDN gRPC TLS)')}"
        )

    @classmethod
    def vless_grpc_cdn_plain(cls, uuid: str, email: str) -> str:
        """4d. VLESS + gRPC через Cloudflare CDN без TLS (порт 80)."""
        from panel.config import CLOUDFLARE_CDN_DOMAIN
        return (
            f"vless://{uuid}@{CLOUDFLARE_CDN_DOMAIN}:80"
            f"?encryption=none&security=none&type=grpc&host={CLOUDFLARE_CDN_DOMAIN}&serviceName=grpc"
            + f"#{quote(f'☁️ {email} (CDN gRPC Plain)')}"
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
            f"#{quote(f'📡 {email} (Relay RU new)')}"
        )

    @staticmethod
    def vless_anti_stub(email: str, uuid: str) -> str:
        """8. VLESS + Reality + Vision — Антизаглушка 4G.

        Тот же relay-сервер, но на нестандартном порту с локальным SNI.
        Обходит поведенческий анализ ТСПУ на стандартном порту 443.
        """
        return (
            f"vless://{uuid}@{ANTI_STUB_IP}:{ANTI_STUB_PORT}"
            f"?encryption=none&security=reality"
            f"&sni={ANTI_STUB_SNI}"
            f"&pbk={RELAY_PUBLIC_KEY}"
            f"&sid={RELAY_SHORT_ID}"
            f"&fp={ANTI_STUB_FP}"
            f"&flow=xtls-rprx-vision"
            f"#{quote(f'📶 {email} (тест обхода белых списков)')}"
        )

    @classmethod
    def test_relays(cls, email: str, uuid: str) -> list[str]:
        """9. Список тестовых релеев Яндекса для обхода белых списков."""
        from panel.config import (
            RELAY_PUBLIC_KEY,
            RELAY_SHORT_ID,
            TEST_RELAY_FP,
            TEST_RELAY_IPS,
            TEST_RELAY_PORT,
            TEST_RELAY_SNI,
            TEST_RELAYS_ENABLED,
        )

        links = []
        if not TEST_RELAYS_ENABLED:
            return links

        for idx, ip in enumerate(TEST_RELAY_IPS, 1):
            if ip and ip != "0.0.0.0":
                links.append(
                    f"vless://{uuid}@{ip}:{TEST_RELAY_PORT}"
                    f"?encryption=none&security=reality"
                    f"&sni={TEST_RELAY_SNI}"
                    f"&pbk={RELAY_PUBLIC_KEY}"
                    f"&sid={RELAY_SHORT_ID}"
                    f"&fp={TEST_RELAY_FP}"
                    f"&flow=xtls-rprx-vision"
                    f"#{quote(f'📶 {email} (тест {idx}: {ip})')}"
                )
        return links

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
            f"#{quote(f'📡 {email} (gRPC Relay RU new)')}"
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

    # ── Наборы ссылок ────────────────────────────────────────────

    @classmethod
    def _relay_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Relay-ссылки (через Яндекс ВМ) — приоритетные для мобильных операторов."""
        links: dict[str, str] = {}
        if RELAY_ENABLED:
            links["vless_relay"] = cls.vless_relay(email, uuid)
            links["vless_relay_xhttp"] = cls.vless_relay_xhttp(email, uuid)
            links["vless_relay_grpc"] = cls.vless_relay_grpc(email, uuid)

        from panel.config import TEST_RELAYS_ENABLED
        if TEST_RELAYS_ENABLED:
            for idx, link in enumerate(cls.test_relays(email, uuid), 1):
                links[f"vless_test_relay_{idx}"] = link
        return links

    @classmethod
    def _direct_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Прямые ссылки (к US серверу) — резервные для WiFi/стабильных сетей."""
        return {
            "vless_reality": cls.vless_reality(uuid, email),
            "vless_xhttp": cls.vless_xhttp(uuid, email),
            "vless_grpc": cls.vless_grpc(uuid, email),
            "vless_ws": cls.vless_ws(uuid, email),
            "vless_ws_cdn": cls.vless_ws_cdn(uuid, email),
            "vless_ws_cdn_plain": cls.vless_ws_cdn_plain(uuid, email),
            "vless_grpc_cdn": cls.vless_grpc_cdn(uuid, email),
            "vless_grpc_cdn_plain": cls.vless_grpc_cdn_plain(uuid, email),
            "hysteria2": cls.hysteria2(email),
            "shadowsocks": cls.shadowsocks(email),
        }

    @classmethod
    def all_links(cls, uuid: str, email: str) -> dict[str, str]:
        """Все каналы: сначала relay (мобильные операторы), потом direct (WiFi).

        Порядок важен — Happ/Hiddify при автовыборе берёт
        первый работающий, поэтому relay идут первыми.
        """
        links: dict[str, str] = {}
        links.update(cls._relay_links(uuid, email))
        links.update(cls._direct_links(uuid, email))
        return links

    @classmethod
    def hiddify_links(cls, uuid: str, email: str, routing: str = None) -> dict[str, str]:
        """Все каналы для Hiddify: relay первыми, direct вторыми."""
        links: dict[str, str] = {}
        links.update(cls._relay_links(uuid, email))
        if routing != "ru":
            links.update(cls._direct_links(uuid, email))
        return links

    @classmethod
    def happ_links(cls, uuid: str, email: str, routing: str = None) -> dict[str, str]:
        """Каналы для Happ (iOS): только стабильные протоколы.

        iOS убивает long-lived HTTP POST при переключении приложений,
        поэтому xHTTP stream-up исключён. Оставлены только TCP/H2-based:
          1. Vision Relay  — основной (TCP, лучший пинг из РФ)
          2. gRPC Relay    — резервный (HTTP/2, мультиплекс)
          3. Vision Direct — аварийный (если relay упадёт)
          4. WS CDN TLS    — сверхнадежный обход блокировок через Cloudflare (порт 443)
          5. WS CDN Plain  — WebSocket на порту 80 (без TLS, обход ТСПУ)
          6. gRPC CDN TLS  — gRPC через Cloudflare (порт 443)
          7. gRPC CDN Plain— gRPC через Cloudflare на порту 80 (без TLS)
        """
        links: dict[str, str] = {}
        if RELAY_ENABLED:
            links["vless_relay"] = cls.vless_relay(email, uuid)
            links["vless_relay_grpc"] = cls.vless_relay_grpc(email, uuid)
            links["vless_anti_stub"] = cls.vless_anti_stub(email, uuid)
        links["vless_reality"] = cls.vless_reality(uuid, email)
        links["vless_ws_cdn"] = cls.vless_ws_cdn(uuid, email)
        links["vless_ws_cdn_plain"] = cls.vless_ws_cdn_plain(uuid, email)
        links["vless_grpc_cdn"] = cls.vless_grpc_cdn(uuid, email)
        links["vless_grpc_cdn_plain"] = cls.vless_grpc_cdn_plain(uuid, email)
        return links

    @classmethod
    def happ_test_links(cls, uuid: str, email: str, routing: str = None) -> dict[str, str]:
        """Ссылки для тестирования в Happ (только стабильные + тестовый DNS профиль)."""
        links: dict[str, str] = {}
        
        # Временно исключаем xHTTP ссылки из-за несовместимости с ядром Happ (sing-box) на iOS,
        # которая приводила к ошибке "критическая ошибка ядра xcore".
        
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

