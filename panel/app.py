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
from fastapi.responses import FileResponse, HTMLResponse
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
    INBOUND_TAG_VISION_2,
    INBOUND_TAG_GRPC_2,

    SERVER_IP,
    SUB_HOST,
    SUB_PORT,
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
from panel.relay_sync import add_user_to_relay, remove_user_from_relay, sync_all_users_to_relay

# ── Bot DB trial reset ────────────────────────────────────────
_BOT_DB_PATH = BOT_DB_PATH


def _reset_bot_trial(email: str):
    """Сброс has_trial в БД бота при удалении пользователя из панели."""
    import sqlite3
    clean = email.lstrip("@")
    try:
        with sqlite3.connect(_BOT_DB_PATH) as conn:
            conn.execute(
                "UPDATE users SET has_trial = 0 WHERE username = ?",
                (clean,),
            )
            conn.commit()
            logger.info("Bot trial reset for %s", clean)
    except Exception as e:
        logger.warning("Failed to reset bot trial for %s: %s", clean, e)


def _build_userinfo(user: dict) -> str:
    """Формирует Subscription-UserInfo с реальными данными пользователя.

    Happ/Sing-Box парсит этот заголовок для отображения статуса:
    - upload/download — трафик в байтах
    - total — лимит трафика в байтах
    - expire — Unix timestamp истечения подписки
    """
    used_bytes = int((user.get("used_gb") or 0) * (1024 ** 3))
    total_bytes = int((user.get("total_gb") or 0) * (1024 ** 3))
    expire_ts = 0
    raw_expires = user.get("expires_at")
    if raw_expires:
        try:
            clean = raw_expires.replace("Z", "+00:00")
            # Добавляем UTC, если timezone отсутствует
            if "+" not in clean[10:] and "-" not in clean[11:]:
                clean += "+00:00"
            dt = datetime.fromisoformat(clean)
            expire_ts = int(dt.timestamp())
        except (ValueError, OSError):
            pass
    return f"upload=0; download={used_bytes}; total={total_bytes}; expire={expire_ts}"


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
    INBOUND_TAG_VISION_2,
    INBOUND_TAG_GRPC_2,
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
            if ENABLE_TRAFFIC_LIMITS:
                traffic_by_email = {}
                
                # 1. Сбор локального трафика (US сервер)
                if xray_client and xray_client.is_connected():
                    try:
                        stats = xray_client.query_stats(reset=True)
                        for stat in stats:
                            parts = stat["name"].split(">>>")
                            # name format: user>>>email>>>traffic>>>downlink
                            if len(parts) == 4 and parts[0] == "user" and parts[2] == "traffic":
                                email = parts[1]
                                value_gb = stat["value"] / (1024**3)
                                traffic_by_email[email] = traffic_by_email.get(email, 0.0) + value_gb
                    except Exception as e:
                        logger.error("Error querying local traffic stats: %s", e)
                
                # 2. Сбор трафика с Relay
                try:
                    from panel.relay_sync import get_relay_traffic_stats
                    relay_stats = get_relay_traffic_stats()
                    for email, value_gb in relay_stats.items():
                        traffic_by_email[email] = traffic_by_email.get(email, 0.0) + value_gb
                except Exception as e:
                    logger.error("Error querying relay traffic stats: %s", e)

                # 3. Применение лимитов и обновление БД
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
                        if xray_client:
                            xray_client.remove_user_all_inbounds(email, ALL_INBOUND_TAGS)
                        try:
                            remove_user_from_relay(email)
                        except Exception as e:
                            logger.error("Failed to remove user %s from relay: %s", email, e)
                    else:
                        db.update_user(email, used_gb=new_used)
        except Exception as e:
            logger.error("Traffic monitor error: %s", e)
            
        await asyncio.sleep(60)


async def _periodic_xray_sync_task():
    """Периодическая сверка и восстановление пользователей в памяти Xray (раз в 5 минут).
    Защищает от сброса памяти при перезапусках xray.service.
    Добавляет только отсутствующих пользователей, не спамит логи.
    """
    await asyncio.sleep(10)  # Даем время на старт
    while True:
        try:
            if xray_client and xray_client.is_connected():
                # Получаем email'ы уже загруженных в Xray пользователей
                existing_emails: set[str] = set()
                for tag in ALL_INBOUND_TAGS:
                    users_in_inbound = xray_client.get_inbound_users(tag)
                    if users_in_inbound:
                        for u in users_in_inbound:
                            existing_emails.add(u.get("email", ""))

                active_users = [u for u in db.list_users() if u.get("is_active")]
                added = 0
                for u in active_users:
                    if u["email"] not in existing_emails:
                        xray_client.add_user_all_inbounds(u["email"], u["uuid"], ALL_INBOUND_TAGS)
                        added += 1
                if added > 0:
                    logger.info("🔄 Periodic sync: added %d missing users to Xray", added)
                
                # Синхронизация с Relay (если включен)
                try:
                    relay_added = sync_all_users_to_relay(active_users)
                    if relay_added > 0:
                        logger.info("🔄 Periodic Relay sync: added %d users to Relay", relay_added)
                except Exception as e:
                    logger.error("Error in periodic Relay sync: %s", e)
        except Exception as e:
            logger.error("Error in periodic Xray sync: %s", e)
        await asyncio.sleep(300)  # 5 минут


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

    # Синхронизация с relay при старте (в фоне, не блокируем)
    try:
        active_users = db.list_users()
        relay_count = sync_all_users_to_relay(active_users)
        if relay_count:
            logger.info("🔄 Relay sync: %d users", relay_count)
    except Exception as e:
        logger.warning("Relay sync failed (non-critical): %s", e)

    ip_task = asyncio.create_task(ip_limiter.start())
    traffic_task = asyncio.create_task(_traffic_monitor_task())
    sync_task = asyncio.create_task(_periodic_xray_sync_task())
    logger.info("🚀 Subscription Manager started (port 8085)")
    yield
    ip_limiter.stop()
    ip_task.cancel()
    traffic_task.cancel()
    sync_task.cancel()
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
    if request.url.path.startswith("/sub/"):
        # no-cache: клиент ОБЯЗАН валидировать через ETag перед использованием кэша
        # Ранее max-age=86400 приводил к тому, что профиль не обновлялся (Проблема 3)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    else:
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


@app.get(
    "/users/{email}",
    response_model=UserResponse,
    dependencies=[Depends(verify_api_key)],
    tags=["Пользователи"],
    summary="Получить пользователя",
)
async def get_user_by_email(email: str):
    """Получить информацию о пользователе по email."""
    user = db.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
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

    # Добавляем на relay
    add_user_to_relay(data.email, data.uuid)

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

    # Удаление из relay
    remove_user_from_relay(email)

    # Сброс trial в БД бота (username = email без @)
    _reset_bot_trial(email)

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
    # Формируем базовый URL подписок с учетом SUB_PORT и протокола (HTTPS на 8086)
    proto = "https" if SUB_PORT in (443, 8086) else "http"
    port_suffix = f":{SUB_PORT}" if SUB_PORT not in (80, 443) else ""
    base = f"{proto}://{SUB_HOST}{port_suffix}/sub"
    return SubscriptionLinks(
        email=email,
        # Стандартные подписки
        sub_happ=f"{base}/happ/{token}",
        sub_happ_android=f"{base}/happ-android/{token}",
        sub_hiddify=f"{base}/hiddify/{token}",
        sub_url=f"{base}/{token}",
        # С маршрутизацией (обход РФ)
        sub_happ_routing=f"{base}/happ/{token}?routing=ru",
        sub_happ_android_routing=f"{base}/happ-android/{token}?routing=ru",
        sub_hiddify_routing=f"{base}/hiddify/{token}?routing=ru",
        sub_url_routing=f"{base}/{token}?routing=ru",
        # Отдельные протоколы
        **links,
        all_links=list(links.values()),
    )


def _find_user_by_token_or_email(token_or_email: str) -> Optional[dict]:
    """Умный поиск пользователя по токену подписки или по email.

    Поддерживает:
    - Поиск по sub_token (e.g. sDVR8UVcriZHSkba9rCAe-ldGozaU_4X)
    - Поиск по email (e.g. @vitaly_gmyza)
    - Поиск по email без собачки (e.g. vitaly_gmyza)
    """
    # 1. Поиск по sub_token
    user = db.get_user_by_token(token_or_email)
    if user:
        return user

    # 2. Поиск по email
    user = db.get_user(token_or_email)
    if user:
        return user

    # 3. Поиск по email с собачкой
    if not token_or_email.startswith("@"):
        user = db.get_user(f"@{token_or_email}")
        if user:
            return user

    return None


@app.api_route(
    "/sub/{token}",
    methods=["GET", "HEAD"],
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

    user = _find_user_by_token_or_email(token)
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
        "Profile-Update-Interval": "24",
        "Subscription-UserInfo": _build_userinfo(user),
    }

    if routing == "ru":
        headers["routing"] = _build_happ_routing_deeplink(_ANDROID_ROUTING_PROFILE)
        headers["no-limit-enabled"] = "1"

    return Response(
        content=text,
        media_type="text/plain",
        headers=headers,
    )


@app.api_route(
    "/sub/hiddify/{token}",
    methods=["GET", "HEAD"],
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

    user = _find_user_by_token_or_email(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Subscription expired")

    text = LinkGenerator.subscription_text_hiddify(user["uuid"], user["email"], routing=routing)
    profile_title = user["email"]

    headers = {
        "Content-Disposition": f'attachment; filename="{user["email"]}_hiddify.txt"',
        "Profile-Title": profile_title,
        "Profile-Update-Interval": "24",
        "Subscription-UserInfo": _build_userinfo(user),
    }

    if routing == "ru":
        headers["routing"] = _build_happ_routing_deeplink(_ANDROID_ROUTING_PROFILE)
        headers["no-limit-enabled"] = "1"

    return Response(
        content=text,
        media_type="text/plain",
        headers=headers,
    )


def _happ_response_headers(
    user: dict,
    routing: Optional[str],
    profile: dict,
    filename_suffix: str = "happ",
    allow_per_app_test: bool = False,
) -> dict:
    """Общие заголовки Happ-подписки для заданного профиля маршрутизации.

    per-app-proxy — Android-only фича Happ, поэтому ru-test ветка
    (allow_per_app_test=True) подключается только на Android-эндпоинте.
    """
    headers = {
        "Content-Disposition": f'inline; filename="{user["email"]}_{filename_suffix}.txt"',
        "Profile-Title": user["email"],
        "Profile-Update-Interval": "24",
        "Subscription-UserInfo": _build_userinfo(user),
    }
    if routing == "ru":
        headers["routing"] = _build_happ_routing_deeplink(profile)
        headers["no-limit-enabled"] = "1"
    elif routing == "ru-test" and allow_per_app_test:
        # Тестовая ветка: тот же профиль + per-app bypass (MAX/банки/
        # маркетплейсы) для проверки на реальном устройстве перед
        # раскаткой на всех Android-пользователей.
        headers["routing"] = _build_happ_routing_deeplink(profile)
        headers["no-limit-enabled"] = "1"
        headers.update(_build_per_app_proxy_headers())
    return headers


@app.api_route(
    "/sub/happ/{token}",
    methods=["GET", "HEAD"],
    tags=["Подписки"],
    summary="Подписка для Happ — iOS / Windows (Base64)",
    description="Оптимизированный набор ссылок для Happ/Sing-Box (iOS, Windows). Добавьте ?routing=ru для обхода РФ",
)
@limiter.limit("30/minute")
async def subscription_happ_endpoint(
    request: Request, token: str, routing: Optional[str] = None
):
    """Подписка Happ для iOS/Windows.

    Профиль маршрутизации использует облегчённые geoip-light.dat/geosite-light.dat
    (PRIVATE+RU, ~30-400 КБ) вместо полных файлов (~28 МБ суммарно) — полные
    файлы роняют VPN-модуль Happ на iOS из-за лимита памяти Network Extension
    (~15-50 МБ в зависимости от версии iOS). geosite:category-ru/geoip:ru
    при этом включены — раздельное туннелирование РФ-сайтов работает.
    Без gRPC (Happ не поддерживает). Кодировка Base64 для совместимости.
    ?routing=ru — включает профиль маршрутизации (обход РФ).
    """
    import base64

    user = _find_user_by_token_or_email(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Subscription expired")

    text = LinkGenerator.subscription_text_happ(user["uuid"], user["email"], routing=routing)
    b64_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    headers = _happ_response_headers(user, routing, _HAPP_ROUTING_PROFILE, "happ")

    return Response(
        content=b64_text,
        media_type="text/plain",
        headers=headers,
    )


@app.api_route(
    "/sub/happ-android/{token}",
    methods=["GET", "HEAD"],
    tags=["Подписки"],
    summary="Подписка для Happ — Android (Base64)",
    description="Набор ссылок для Happ/Sing-Box на Android с полным профилем обхода РФ (geoip:ru + geosite:category-ru). Добавьте ?routing=ru",
)
@limiter.limit("30/minute")
async def subscription_happ_android_endpoint(
    request: Request, token: str, routing: Optional[str] = None
):
    """Подписка Happ для Android.

    Полный профиль маршрутизации (geoip:ru + geosite:category-ru, полные
    geoip.dat/geosite.dat) — весь российский трафик, включая MAX, банки и
    маркетплейсы, идёт напрямую мимо VPN. На Android нет ограничения по
    памяти Network Extension, как на iOS, поэтому точность важнее размера.
    ?routing=ru — базовый профиль обхода РФ.
    ?routing=ru-test — то же + нативный per-app VPN bypass (MAX/банки/
    маркетплейсы получают реальное прямое подключение на уровне ОС,
    не только через доменные правила). Тестируется перед раскаткой всем.
    """
    import base64

    user = _find_user_by_token_or_email(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Subscription expired")

    text = LinkGenerator.subscription_text_happ(user["uuid"], user["email"], routing=routing)
    b64_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    headers = _happ_response_headers(
        user, routing, _ANDROID_ROUTING_PROFILE, "happ_android", allow_per_app_test=True
    )

    return Response(
        content=b64_text,
        media_type="text/plain",
        headers=headers,
    )


@app.api_route(
    "/sub/happ-test/{token}",
    methods=["GET", "HEAD"],
    tags=["Подписки"],
    summary="Тестовая подписка для Happ (Base64)",
    description="Набор ссылок с тестовыми xHTTP протоколами (auto и stream-one). Добавьте ?routing=ru для обхода РФ",
)
@limiter.limit("30/minute")
async def subscription_happ_test_endpoint(
    request: Request, token: str, routing: Optional[str] = None
):
    """Тестовая подписка Happ с xHTTP (auto и stream-one)."""
    import base64

    user = _find_user_by_token_or_email(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Subscription expired")

    text = LinkGenerator.subscription_text_happ_test(user["uuid"], user["email"], routing=routing)
    b64_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    profile_title = f"TEST Happ {user['email']}"

    headers = {
        "Content-Disposition": f'inline; filename="{user["email"]}_happ_test.txt"',
        "Profile-Title": profile_title,
        "Profile-Update-Interval": "24",
        "Subscription-UserInfo": _build_userinfo(user),
    }

    if routing == "ru":
        headers["routing"] = _build_happ_routing_deeplink(_HAPP_TEST_ROUTING_PROFILE)
        headers["no-limit-enabled"] = "1"

    return Response(
        content=b64_text,
        media_type="text/plain",
        headers=headers,
    )


@app.api_route(
    "/sub/amnezia/{token}",
    methods=["GET", "HEAD"],
    tags=["Подписки"],
    summary="Подписка для AmneziaVPN",
    description="Список ссылок в чистом виде для парсера Amnezia",
)
@limiter.limit("30/minute")
async def subscription_amnezia_endpoint(request: Request, token: str):

    user = _find_user_by_token_or_email(token)
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
            "Profile-Update-Interval": "24",
        },
    )


# ── Happ Routing Profile (Russia Bypass) ──────────────────────

_HAPP_ROUTING_PROFILE = {
    "Name": "🇷🇺 Обход РФ",
    "GlobalProxy": "true",
    "RemoteDNSType": "DoH",
    "RemoteDNSDomain": "https://dns.google/dns-query",
    "RemoteDNSIP": "8.8.8.8",
    "DomesticDNSType": "DoH",
    "DomesticDNSDomain": "https://common.dns.yandex.ru/dns-query",
    "DomesticDNSIP": "77.88.8.8",
    # Облегчённые файлы (PRIVATE+RU / PRIVATE+CATEGORY-RU, ~30-400 КБ) —
    # iOS Network Extension ограничен по памяти (~15-50 МБ), полные geoip.dat/
    # geosite.dat (18/10 МБ) роняли VPN-модуль Happ. Android override — ниже,
    # у него нет такого ограничения, поэтому получает полные файлы.
    "Geoipurl": "https://sub.synthosai.ru:8086/sub/geo/geoip-light.dat",
    "Geositeurl": "https://sub.synthosai.ru:8086/sub/geo/geosite-light.dat",
    "DnsHosts": {
        "cloudflare-dns.com": "1.1.1.1",
        "dns.google": "8.8.8.8",
        "common.dns.yandex.ru": "77.88.8.8",
        "38.180.81.181.sslip.io": "185.4.67.223",
        "sub.synthosai.ru": "185.4.67.223",
    },
    "DirectSites": [
        # Наш домен подписки — всегда напрямую (без VPN), чтобы избежать петель маршрутизации
        "domain:synthosai.ru",
        # Резервный домен CDN — напрямую, чтобы избежать петель маршрутизации
        "domain:fredom.ru",
        # Все домены зоны .ru — напрямую без VPN
        "domain:ru",
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
    "DomainStrategy": "IPIfNonMatch",
    "FakeDNS": "false",
}


_ANDROID_ROUTING_PROFILE = {
    **_HAPP_ROUTING_PROFILE,
    # Android не ограничен по памяти Network Extension — получает полные
    # geoip.dat/geosite.dat (точнее классификация, чем в light-версии для iOS).
    # geosite:category-ru/geoip:ru уже в базовом профиле (_HAPP_ROUTING_PROFILE),
    # здесь их дублировать не нужно.
    "Geoipurl": "https://sub.synthosai.ru:8086/sub/geo/geoip.dat",
    "Geositeurl": "https://sub.synthosai.ru:8086/sub/geo/geosite.dat",
}


# ── Per-App VPN Bypass (Android, VpnService-level) ────────────
# Приложения детектируют NetworkCapabilities.TRANSPORT_VPN независимо от
# geoip/geosite маршрутизации внутри туннеля (это флаг ОС, а не маршрут
# трафика). Единственный способ дать им реальное прямое подключение —
# нативный per-app bypass в Happ (addDisallowedApplication на уровне
# VpnService.Builder), а не доменные правила. Не убирает сам факт наличия
# VPN на устройстве (см. INCIDENT_LOG 2026-07-17), но чинит совместную
# работу этих приложений с активным VPN-туннелем.
_ANDROID_PER_APP_BYPASS_PACKAGES = [
    "ru.oneme.app",                 # MAX
    "ru.sberbankmobile",            # Сбербанк Онлайн
    "com.idamob.tinkoff.android",   # Т-Банк (Тинькофф)
    "com.wildberries.ru",           # Wildberries
    "ru.ozon.app.android",          # Ozon
    "ru.rostel",                    # Госуслуги
]


def _build_per_app_proxy_headers() -> dict:
    """Заголовки Happ для реального VpnService-bypass списка приложений."""
    return {
        "per-app-proxy-mode": "bypass",
        "per-app-proxy-list": ",".join(_ANDROID_PER_APP_BYPASS_PACKAGES),
    }


_HAPP_TEST_ROUTING_PROFILE = {
    **_HAPP_ROUTING_PROFILE,
    "RemoteDNSType": "DoH",
    "RemoteDNSDomain": "https://dns.adguard-dns.com/dns-query",
    "RemoteDNSIP": "94.140.14.14",
    "DnsHosts": {
        **_HAPP_ROUTING_PROFILE["DnsHosts"],
        "dns.adguard-dns.com": "94.140.14.14",
    },
    # geosite:category-ru/geoip:ru уже в базовом профиле — не дублируем.
    "BlockSites": [
        # geosite:category-ads-all УБРАН — требует скачивания с GitHub
    ],
}


def _build_happ_routing_deeplink(profile: dict = None) -> str:
    """Генерация deeplink для автоматической настройки маршрутизации в Happ."""
    import base64 as b64mod

    if profile is None:
        profile = _HAPP_ROUTING_PROFILE
    profile_json = json.dumps(profile, ensure_ascii=False)
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

    was_active = bool(user.get("is_active"))
    updated = db.update_user(email, **fields)
    if not updated:
        raise HTTPException(status_code=500, detail="Update failed")

    # Синхронизация с Xray и Relay при изменении статуса активности
    now_active = bool(updated.get("is_active"))
    if now_active != was_active:
        try:
            if now_active:
                if xray_client:
                    xray_client.add_user_all_inbounds(updated["email"], updated["uuid"], ALL_INBOUND_TAGS)
                add_user_to_relay(updated["email"], updated["uuid"])
                logger.info("⚡ Instantly activated user %s in Xray and Relay", email)
            else:
                if xray_client:
                    xray_client.remove_user_all_inbounds(updated["email"], ALL_INBOUND_TAGS)
                remove_user_from_relay(updated["email"])
                logger.info("⚡ Instantly deactivated user %s in Xray and Relay", email)
        except Exception as e:
            logger.error("Failed to instantly sync user %s status: %s", email, e)

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


@app.get(
    "/sub/geo/geoip.dat",
    tags=["Подписки"],
    summary="Скачать geoip.dat локально",
    description="Раздача файла geoip.dat с нашего сервера для обхода блокировок GitHub в РФ",
)
async def get_geoip():
    file_path = "/var/lib/vpn-panel/geo/geoip.dat"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/octet-stream", filename="geoip.dat")
    raise HTTPException(status_code=404, detail="GeoIP file not found")


@app.get(
    "/sub/geo/geosite.dat",
    tags=["Подписки"],
    summary="Скачать geosite.dat локально",
    description="Раздача файла geosite.dat с нашего сервера для обхода блокировок GitHub в РФ",
)
async def get_geosite():
    file_path = "/var/lib/vpn-panel/geo/geosite.dat"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/octet-stream", filename="geosite.dat")
    raise HTTPException(status_code=404, detail="GeoSite file not found")


@app.get(
    "/sub/geo/geoip-light.dat",
    tags=["Подписки"],
    summary="Скачать облегчённый geoip.dat (PRIVATE+RU) для iOS",
    description=(
        "Урезанная версия geoip.dat — только коды PRIVATE и RU (~390 КБ вместо ~18 МБ). "
        "Нужна для iOS: Network Extension Happ ограничен по памяти (~15-50 МБ) и не "
        "выдерживает загрузку полного geoip.dat. См. scripts/build_geo_light.py."
    ),
)
async def get_geoip_light():
    file_path = "/var/lib/vpn-panel/geo/geoip-light.dat"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/octet-stream", filename="geoip-light.dat")
    raise HTTPException(status_code=404, detail="GeoIP light file not found")


@app.get(
    "/sub/geo/geosite-light.dat",
    tags=["Подписки"],
    summary="Скачать облегчённый geosite.dat (PRIVATE+CATEGORY-RU) для iOS",
    description=(
        "Урезанная версия geosite.dat — только коды PRIVATE и CATEGORY-RU (~26 КБ вместо ~10 МБ). "
        "Нужна для iOS: Network Extension Happ ограничен по памяти (~15-50 МБ) и не "
        "выдерживает загрузку полного geosite.dat. См. scripts/build_geo_light.py."
    ),
)
async def get_geosite_light():
    file_path = "/var/lib/vpn-panel/geo/geosite-light.dat"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/octet-stream", filename="geosite-light.dat")
    raise HTTPException(status_code=404, detail="GeoSite light file not found")


