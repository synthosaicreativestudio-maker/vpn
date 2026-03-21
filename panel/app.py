"""Subscription Manager API — Главное приложение FastAPI.

Запуск:
    uvicorn panel.app:app --host 0.0.0.0 --port 8085

Документация:
    http://localhost:8085/docs
"""

import asyncio
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
from starlette.middleware.trustedhost import TrustedHostMiddleware

from panel.config import (
    API_KEY,
    API_KEY_HEADER,
    BOT_DB_PATH,
    DB_PATH,
    DEFAULT_IP_LIMIT,
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


# ── Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(application: FastAPI):
    _init_xray_client()
    ip_task = asyncio.create_task(ip_limiter.start())
    logger.info("🚀 Subscription Manager started (port 8085)")
    yield
    ip_limiter.stop()
    ip_task.cancel()
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
    return SubscriptionLinks(
        email=email,
        sub_url=f"http://{SERVER_IP}:8085/sub/{user['sub_token']}",
        **links,
        all_links=list(links.values()),
    )


@app.get(
    "/sub/{token}",
    tags=["Подписки"],
    summary="Публичная подписка",
    description="Текстовый список ссылок для Hiddify/Happ (без ключа API)",
)
@limiter.limit("30/minute")
async def subscription_endpoint(request: Request, token: str):
    """Публичный endpoint подписки (без API key).

    Клиент (Hiddify/Happ) использует этот URL для автоматического
    обновления конфигурации.
    """
    import base64

    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Subscription expired")

    text = LinkGenerator.subscription_text(user["uuid"], user["email"])
    profile_title = base64.b64encode(
        f"🛡 VPN {user['email']}".encode()
    ).decode()
    return Response(
        content=text,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{user["email"]}.txt"',
            "Profile-Title": profile_title,
            "Profile-Update-Interval": "12",
            "Subscription-UserInfo": "upload=0; download=0; total=0; expire=0",
        },
    )


@app.get(
    "/sub/happ/{token}",
    tags=["Подписки"],
    summary="Подписка для Happ (Base64)",
    description="Закодированный в Base64 список ссылок для iOS-клиентов вроде Happ",
)
@limiter.limit("30/minute")
async def subscription_happ_endpoint(request: Request, token: str):
    """Специальный endpoint для Happ (Sing-Box), требующего Base64 формат."""
    import base64

    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Subscription expired")

    text = LinkGenerator.subscription_text(user["uuid"], user["email"])
    b64_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    
    profile_title = base64.b64encode(
        f"🛡 Happ VPN {user['email']}".encode()
    ).decode()
    
    return Response(
        content=b64_text,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{user["email"]}_happ.txt"',
            "Profile-Title": profile_title,
            "Profile-Update-Interval": "12",
        },
    )


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
