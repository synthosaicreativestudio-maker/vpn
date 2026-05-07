"""Subscription Manager API — Главное приложение FastAPI.

Запуск:
    uvicorn panel.app:app --host 0.0.0.0 --port 8085

Документация:
    http://localhost:8085/docs
"""

import asyncio
import json
import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security.api_key import APIKeyHeader
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from panel.config import (
    API_KEY,
    API_KEY_HEADER,
    BOT_DB_PATH,
    DB_PATH,
    DEFAULT_IP_LIMIT,
    ENABLE_TRAFFIC_LIMITS,
    INBOUND_TAG_GRPC,
    INBOUND_TAG_VISION,
    INBOUND_TAG_WS,
    INBOUND_TAG_XHTTP,
    SERVER_IP,
    XRAY_GRPC_HOST,
)
from panel.db import PanelDB
from panel.ip_limiter import IPLimiter
from panel.link_generator import LinkGenerator
from panel.models import (
    HealthResponse,
    SubscriptionLinks,
    UserCreate,
    UserResponse,
    UserStats,
    UserUpdate,
)

# ── Templates ─────────────────────────────────────────────────
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_TEMPLATES_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("panel")

# ── Глобальные объекты ────────────────────────────────────────
db = PanelDB(DB_PATH)
ip_limiter = IPLimiter(db)

ALL_INBOUND_TAGS = [
    INBOUND_TAG_VISION,
    INBOUND_TAG_XHTTP,
    INBOUND_TAG_GRPC,
    INBOUND_TAG_WS,
]

# Xray клиент (может быть None если stubs ещё не сгенерированы)
xray_client: Optional[object] = None


def _init_xray_client():
    """Попытка подключения к Xray gRPC."""
    global xray_client
    try:
        from panel.xray_client import XrayClient

        xray_client = XrayClient(XRAY_GRPC_HOST)
        logger.info("Xray gRPC client initialized")
    except RuntimeError:
        logger.warning(
            "Xray gRPC unavailable — working in offline mode. "
            "Run: cd panel/proto && bash generate.sh"
        )
        xray_client = None


async def _traffic_monitor_task():
    """Фоновая задача опроса статистики Xray и обновления БД."""
    while True:
        try:
            if ENABLE_TRAFFIC_LIMITS and xray_client and xray_client.is_connected():
                stats = xray_client.query_stats(reset=True)
                traffic_by_email = {}
                for stat in stats:
                    parts = stat["name"].split(">>>")
                    # name format: user>>>email>>>traffic>>>downlink
                    if len(parts) == 4 and parts[0] == "user" and parts[2] == "traffic":
                        email = parts[1]
                        value_gb = stat["value"] / (1024**3)
                        traffic_by_email[email] = traffic_by_email.get(email, 0.0) + value_gb

                for email, added_gb in traffic_by_email.items():
                    if added_gb <= 0:
                        continue
                    user = db.get_user(email)
                    if not user:
                        continue
                    new_used = (user.get("used_gb") or 0.0) + added_gb
                    total_gb = user.get("total_gb") or 0.0
                    
                    if total_gb > 0 and new_used >= total_gb and user.get("is_active"):
                        logger.warning("User %s exceeded traffic limit (%.2f/%.2f GB). Disabling.", email, new_used, total_gb)
                        db.update_user(email, used_gb=new_used, is_active=0)
                        xray_client.remove_user_all_inbounds(email, ALL_INBOUND_TAGS)
                    else:
                        db.update_user(email, used_gb=new_used)
        except Exception as e:
            logger.error("Traffic monitor error: %s", e)
            
        await asyncio.sleep(60)


# ── Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(application: FastAPI):
    _init_xray_client()
    
    # Ресинхронизация пользователей при старте
    if xray_client:
        try:
            users = db.list_users()
            sync_count = 0
            for u in users:
                if u.get("is_active"):
                    xray_client.add_user_all_inbounds(u["email"], u["uuid"], ALL_INBOUND_TAGS)
                    sync_count += 1
            logger.info(f"🔄 Resynced {sync_count} active users to Xray memory")
        except Exception as e:
            logger.error(f"Failed to resync users: {e}")

    ip_task = asyncio.create_task(ip_limiter.start())
    traffic_task = asyncio.create_task(_traffic_monitor_task())
    logger.info("🚀 Subscription Manager started (port 8085)")
    yield
    ip_limiter.stop()
    ip_task.cancel()
    traffic_task.cancel()
    if xray_client:
        xray_client.close()
    logger.info("Subscription Manager stopped")


# ── Rate Limiter ──────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── Группировка эндпоинтов (Tags) ─────────────────────────────
tags_metadata = [
    {
        "name": "Система",
        "description": "Проверка статуса и здоровья сервиса.",
    },
    {
        "name": "Пользователи",
        "description": "Управление пользователями: создание, удаление, список.",
    },
    {
        "name": "Подписки",
        "description": "Генерация ссылок для клиентов (Hiddify, и др.).",
    },
]

app = FastAPI(
    title="Менеджер Подписок",
    description="Панель управления VPN-подписками через Xray gRPC (Март 2026)",
    version="2026.1.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware Stack (OWASP API Top 10) ───────────────────────

# 1. CORS — только доверенные источники
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"https://{SERVER_IP}", "https://localhost"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=[API_KEY_HEADER],
)

# 2. TrustedHost отключен, так как мы за Caddy


# 3. Security Headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Добавляет security headers ко всем ответам."""
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=()"
    response.headers["Cache-Control"] = "no-store"
    return response

# ── Security ──────────────────────────────────────────────────
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


async def verify_api_key(
    key: str = Security(api_key_header),
):
    if key == API_KEY:
        return key
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API key",
    )


# ── Endpoints ─────────────────────────────────────────────────


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Система"],
    summary="Состояние сервиса",
)
@limiter.limit("30/minute")
async def health_check(request: Request):
    """Статус сервиса и подключения к Xray."""
    connected = False
    if xray_client:
        connected = xray_client.is_connected()
    return HealthResponse(
        status="online",
        version="2026.1.0",
        xray_connected=connected,
    )


@app.get(
    "/stats",
    response_model=UserStats,
    dependencies=[Depends(verify_api_key)],
    tags=["Система"],
    summary="Статистика базы",
)
async def get_stats():
    """Статистика по пользователям."""
    return db.get_stats()


@app.get(
    "/users",
    dependencies=[Depends(verify_api_key)],
    tags=["Пользователи"],
    summary="Список всех пользователей",
)
async def list_users():
    """Список всех пользователей."""
    users = db.list_users()
    return {"users": users, "count": len(users)}


@app.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
    tags=["Пользователи"],
    summary="Создать пользователя",
)
@limiter.limit("10/minute")
async def create_user(request: Request, data: UserCreate):
    """Создать нового пользователя и добавить во все inbound'ы Xray."""
    # Проверка уникальности
    if db.get_user(data.email):
        raise HTTPException(
            status_code=409, detail=f"User {data.email} already exists"
        )

    # Генерация токена подписки
    sub_token = secrets.token_urlsafe(24)

    # Добавление в Xray (если gRPC доступен)
    if xray_client:
        results = xray_client.add_user_all_inbounds(
            data.email, data.uuid, ALL_INBOUND_TAGS
        )
        failed = [tag for tag, ok in results.items() if not ok]
        if failed:
            logger.warning("Failed to add user to inbounds: %s", failed)

    # Сохранение в БД
    user = db.add_user(
        email=data.email,
        uuid=data.uuid,
        ip_limit=data.ip_limit or DEFAULT_IP_LIMIT,
        sub_token=sub_token,
        expire_days=data.expire_days,
        description=data.description,
    )

    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")

    return UserResponse(
        email=user["email"],
        uuid=user["uuid"],
        ip_limit=user["ip_limit"],
        created_at=user["created_at"],
        expires_at=user.get("expires_at"),
        is_active=bool(user["is_active"]),
        sub_token=user["sub_token"],
        phone=user.get("phone"),
        total_gb=user.get("total_gb") or 0.0,
        used_gb=user.get("used_gb") or 0.0,
    )


@app.delete(
    "/users/{email}",
    dependencies=[Depends(verify_api_key)],
    tags=["Пользователи"],
    summary="Удалить пользователя",
)
@limiter.limit("10/minute")
async def delete_user(request: Request, email: str):
    """Удалить пользователя из Xray и БД."""
    user = db.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Удаление из Xray
    if xray_client:
        xray_client.remove_user_all_inbounds(email, ALL_INBOUND_TAGS)

    # Удаление из БД
    db.delete_user(email)

    return {"message": f"User {email} deleted"}


@app.get(
    "/users/{email}/links",
    response_model=SubscriptionLinks,
    dependencies=[Depends(verify_api_key)],
    tags=["Подписки"],
    summary="Получить все ссылки",
)
async def get_user_links(email: str):
    """Получить все ссылки подписки для пользователя."""
    user = db.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    links = LinkGenerator.all_links(user["uuid"], email)
    token = user["sub_token"]
    return SubscriptionLinks(
        email=email,
        # Стандартные подписки
        sub_url=f"http://{SERVER_IP}:8085/sub/{token}",
        sub_hiddify=f"http://{SERVER_IP}:8085/sub/hiddify/{token}",
        sub_happ=f"https://{SERVER_IP}.sslip.io:8086/sub/happ/{token}",
        sub_amnezia=f"http://{SERVER_IP}:8085/sub/amnezia/{token}",
        # С маршрутизацией (обход РФ)
        sub_url_routing=f"http://{SERVER_IP}:8085/sub/{token}?routing=ru",
        sub_hiddify_routing=f"http://{SERVER_IP}:8085/sub/hiddify/{token}?routing=ru",
        sub_happ_routing=f"https://{SERVER_IP}.sslip.io:8086/sub/happ/{token}?routing=ru",
        **links,
        all_links=list(links.values()),
    )


@app.get(
    "/sub/{token}",
    tags=["Подписки"],
    summary="Публичная подписка (универсальная)",
    description="Все ссылки для любого клиента. Добавьте ?routing=ru для обхода РФ",
)
@limiter.limit("30/minute")
async def subscription_endpoint(
    request: Request, token: str, routing: Optional[str] = None
):
    """Универсальный endpoint подписки (без API key).

    Содержит все ссылки: VLESS, Hysteria2.
    Совместим с Hiddify, Happ и другими клиентами.
    ?routing=ru — включает профиль маршрутизации (обход РФ).
    """

    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Subscription expired")

    text = LinkGenerator.subscription_text(user["uuid"], user["email"])
    if routing == "ru":
        profile_title = f"VPN + Obhod RF {user['email']}"
    else:
        profile_title = f"VPN {user['email']}"

    headers = {
        "Content-Disposition": f'attachment; filename="{user["email"]}.txt"',
        "Profile-Title": profile_title,
        "Profile-Update-Interval": "12",
        "Subscription-UserInfo": "upload=0; download=0; total=0; expire=0",
    }

    if routing == "ru":
        headers["routing"] = _build_happ_routing_deeplink()
        headers["no-limit-enabled"] = "1"

    return Response(
        content=text,
        media_type="text/plain",
        headers=headers,
    )


@app.get(
    "/sub/hiddify/{token}",
    tags=["Подписки"],
    summary="Подписка для Hiddify",
    description="Оптимизированный набор ссылок для Hiddify. Добавьте ?routing=ru для обхода РФ",
)
@limiter.limit("30/minute")
async def subscription_hiddify_endpoint(
    request: Request, token: str, routing: Optional[str] = None
):
    """Подписка оптимизированная для Hiddify.

    Включает все протоколы: VLESS Vision, xHTTP, gRPC, WS, Hysteria2.
    ?routing=ru — включает профиль маршрутизации (обход РФ).
    """

    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Subscription expired")

    text = LinkGenerator.subscription_text_hiddify(user["uuid"], user["email"])
    if routing == "ru":
        profile_title = f"Hiddify + Obhod RF {user['email']}"
    else:
        profile_title = f"Hiddify VPN {user['email']}"

    headers = {
        "Content-Disposition": f'attachment; filename="{user["email"]}_hiddify.txt"',
        "Profile-Title": profile_title,
        "Profile-Update-Interval": "12",
        "Subscription-UserInfo": "upload=0; download=0; total=0; expire=0",
    }

    if routing == "ru":
        headers["routing"] = _build_happ_routing_deeplink()
        headers["no-limit-enabled"] = "1"

    return Response(
        content=text,
        media_type="text/plain",
        headers=headers,
    )


@app.get(
    "/sub/happ/{token}",
    tags=["Подписки"],
    summary="Подписка для Happ (Base64)",
    description="Оптимизированный набор ссылок для Happ/Sing-Box. Добавьте ?routing=ru для обхода РФ",
)
@limiter.limit("30/minute")
async def subscription_happ_endpoint(
    request: Request, token: str, routing: Optional[str] = None
):
    """Подписка оптимизированная для Happ (Sing-Box).

    Без gRPC (Happ не поддерживает).
    Кодировка Base64 для совместимости.
    ?routing=ru — включает профиль маршрутизации (обход РФ).
    """
    import base64

    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Subscription expired")

    text = LinkGenerator.subscription_text_happ(user["uuid"], user["email"])
    b64_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    if routing == "ru":
        profile_title = f"Happ + Obhod RF {user['email']}"
    else:
        profile_title = f"Happ VPN {user['email']}"

    headers = {
        "Content-Disposition": f'attachment; filename="{user["email"]}_happ.txt"',
        "Profile-Title": profile_title,
        "Profile-Update-Interval": "12",
        "Subscription-UserInfo": "upload=0; download=0; total=0; expire=0",
    }

    if routing == "ru":
        headers["routing"] = _build_happ_routing_deeplink()
        headers["no-limit-enabled"] = "1"

    return Response(
        content=b64_text,
        media_type="text/plain",
        headers=headers,
    )


@app.get(
    "/sub/amnezia/{token}",
    tags=["Подписки"],
    summary="Подписка для AmneziaVPN",
    description="Список ссылок в чистом виде для парсера Amnezia",
)
@limiter.limit("30/minute")
async def subscription_amnezia_endpoint(request: Request, token: str):

    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Subscription expired")

    text = LinkGenerator.subscription_text(user["uuid"], user["email"])
    profile_title = f"Amnezia VPN {user['email']}"

    return Response(
        content=text,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{user["email"]}_amnezia.txt"',
            "Profile-Title": profile_title,
            "Profile-Update-Interval": "12",
        },
    )


# ── Happ Routing Profile (Russia Bypass) ──────────────────────

_HAPP_ROUTING_PROFILE = {
    "Name": "🇷🇺 Обход РФ",
    "GlobalProxy": "true",
    "RemoteDNSType": "DoH",
    "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
    "RemoteDNSIP": "1.1.1.1",
    "DomesticDNSType": "DoH",
    "DomesticDNSDomain": "https://dns.google/dns-query",
    "DomesticDNSIP": "8.8.8.8",
    "Geoipurl": "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat",
    "Geositeurl": "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat",
    "DnsHosts": {
        "cloudflare-dns.com": "1.1.1.1",
        "dns.google": "8.8.8.8",
    },
    "DirectSites": [
        # Все домены зоны .ru — напрямую без VPN
        "domain:ru",
        # Автоматическое определение российских сайтов через geosite
        "geosite:category-ru",
        # CRM и бизнес-сервисы
        "domain:crm.topnlab.ru",
        # Дополнительные домены (CDN/API которых может не быть в geosite)
        "domain:vk.com", "domain:vk.me", "domain:vkontakte.ru",
        "domain:userapi.com", "domain:vk-cdn.net", "domain:vkuser.net",
        "domain:vk.cc", "domain:vkuseraudio.net", "domain:vkuservideo.net",
        "domain:vk-portal.net", "domain:vk.video", "domain:vk-apps.com",
        "domain:vkplay.ru", "domain:vkmusic.ru",
        "domain:ok.ru", "domain:odnoklassniki.ru", "domain:odkl.ru",
        "domain:mail.ru", "domain:max.ru", "domain:max.im",
        "domain:my.mail.ru", "domain:imgsmail.ru", "domain:mycdn.me",
        "domain:mradx.net", "domain:mailru-api.ru", "domain:mr0.ru",
        # Telegram НЕ в DirectSites — заблокирован в РФ, идёт через VPN
        "domain:yandex.ru", "domain:yandex.net", "domain:ya.ru",
        "domain:yastatic.net", "domain:yandex.com",
        "domain:sberbank.ru", "domain:sber.ru",
        "domain:tinkoff.ru", "domain:tbank.ru", "domain:tcsbank.ru",
        "domain:wildberries.ru", "domain:wb.ru", "domain:wbstatic.net",
        "domain:wbbasket.ru", "domain:wbx-content.ru",
        "domain:ozon.ru", "domain:ozoncdn.com", "domain:ozonstat.com",
        "domain:sbermegamarket.ru", "domain:megamarket.ru",
        "domain:sbermarket.ru",
        "domain:gosuslugi.ru", "domain:mos.ru",
        "domain:avito.ru", "domain:avito.st",
        # 2ГИС — карты, навигация, справочник
        "domain:2gis.ru", "domain:2gis.com",
        "domain:2gis.io", "domain:2gis.pro",
    ],
    "DirectIp": [
        # Автоматическое определение российских IP через geoip
        "geoip:ru",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "224.0.0.0/4",
        "255.255.255.255",
    ],
    "ProxySites": [],
    "ProxyIp": [],
    "BlockSites": [],
    "BlockIp": [],
    "DomainStrategy": "AsIs",
    "FakeDNS": "false",
}


def _build_happ_routing_deeplink() -> str:
    """Генерация deeplink для автоматической настройки маршрутизации в Happ."""
    import base64 as b64mod

    profile_json = json.dumps(_HAPP_ROUTING_PROFILE, ensure_ascii=False)
    encoded = b64mod.b64encode(profile_json.encode("utf-8")).decode("utf-8")
    return f"happ://routing/onadd/{encoded}"


@app.get(
    "/routing/happ",
    tags=["Подписки"],
    summary="Профиль маршрутизации для Happ (обход РФ)",
    description="Deeplink для автонастройки маршрутизации: РФ сайты/приложения напрямую, остальное через VPN",
)
@limiter.limit("30/minute")
async def happ_routing_profile(request: Request):
    """Возвращает deeplink для настройки маршрутизации в Happ.

    Российские сайты и приложения идут напрямую (Direct),
    зарубежные сервисы — через VPN-туннель (Proxy).
    Реклама блокируется.
    """
    deeplink = _build_happ_routing_deeplink()
    return {
        "deeplink": deeplink,
        "qr_content": deeplink,
        "instruction": "Откройте эту ссылку на телефоне с установленным Happ, "
        "или отсканируйте QR-код в разделе Маршрутизация → QR-код",
    }


@app.get(
    "/users/{email}/ips",
    dependencies=[Depends(verify_api_key)],
    tags=["Система"],
    summary="Активные IP",
)
async def get_user_ips(email: str):
    """Получить активные IP-адреса пользователя."""
    user = db.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ips = ip_limiter.get_user_ips(email)
    return {
        "email": email,
        "ip_limit": user["ip_limit"],
        "active_ips": ips,
        "count": len(ips),
        "exceeded": len(ips) > user["ip_limit"],
    }


@app.patch(
    "/users/{email}",
    response_model=UserResponse,
    dependencies=[Depends(verify_api_key)],
    tags=["Пользователи"],
    summary="Обновить данные пользователя",
)
async def update_user(email: str, data: UserUpdate):
    """Обновить ip_limit, expires_at, is_active или description."""
    user = db.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    fields: dict = {}
    if data.ip_limit is not None:
        fields["ip_limit"] = data.ip_limit
    if data.is_active is not None:
        fields["is_active"] = 1 if data.is_active else 0
    if data.description is not None:
        fields["description"] = data.description
    if data.expires_at is not None:
        fields["expires_at"] = data.expires_at
    if data.phone is not None:
        fields["phone"] = data.phone
    if data.total_gb is not None:
        fields["total_gb"] = data.total_gb
    if data.used_gb is not None:
        fields["used_gb"] = data.used_gb
    if data.expire_days is not None:
        # Продлить от текущего expires_at или от сегодня
        base = user.get("expires_at")
        if base:
            try:
                base_dt = datetime.fromisoformat(base)
                # Если уже истёк — продлять от сегодня
                if base_dt < datetime.utcnow():
                    base_dt = datetime.utcnow()
            except ValueError:
                base_dt = datetime.utcnow()
        else:
            base_dt = datetime.utcnow()
        fields["expires_at"] = (base_dt + timedelta(days=data.expire_days)).isoformat()

    updated = db.update_user(email, **fields)
    if not updated:
        raise HTTPException(status_code=500, detail="Update failed")

    return UserResponse(
        email=updated["email"],
        uuid=updated["uuid"],
        ip_limit=updated["ip_limit"],
        created_at=updated["created_at"],
        expires_at=updated.get("expires_at"),
        is_active=bool(updated["is_active"]),
        sub_token=updated["sub_token"],
        phone=updated.get("phone"),
        total_gb=updated.get("total_gb") or 0.0,
        used_gb=updated.get("used_gb") or 0.0,
    )


# ── Admin UI ──────────────────────────────────────────────────


@app.get(
    "/admin/users-data",
    dependencies=[Depends(verify_api_key)],
    tags=["Система"],
    summary="Данные пользователей для UI",
)
async def admin_users_data():
    """JSON с объединёнными данными панели и Telegram-бота для дашборда."""
    users = db.get_users_with_tg_info(BOT_DB_PATH)
    health = {"xray_connected": False}
    if xray_client:
        health["xray_connected"] = xray_client.is_connected()
    stats = db.get_stats()
    return {
        "users": users,
        "stats": stats,
        "xray_connected": health["xray_connected"],
    }


@app.get(
    "/admin/ui",
    response_class=HTMLResponse,
    tags=["Система"],
    summary="Веб-дашборд администратора",
)
async def admin_ui(request: Request):
    """HTML-интерфейс управления пользователями."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "server_ip": SERVER_IP,
            "api_key_header": API_KEY_HEADER,
        },
    )
