"""Subscription Manager API — Главное приложение FastAPI.

Запуск:
    uvicorn panel.app:app --host 0.0.0.0 --port 8085

Документация:
    http://localhost:8085/docs
"""

import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Response, Security, status
from fastapi.security.api_key import APIKeyHeader

from panel.config import (
    API_KEY,
    API_KEY_HEADER,
    DB_PATH,
    DEFAULT_IP_LIMIT,
    INBOUND_TAG_GRPC,
    INBOUND_TAG_VISION,
    INBOUND_TAG_XHTTP,
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
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("panel")

# ── Глобальные объекты ────────────────────────────────────────
db = PanelDB(DB_PATH)
ip_limiter = IPLimiter(db)

ALL_INBOUND_TAGS = [INBOUND_TAG_VISION, INBOUND_TAG_XHTTP, INBOUND_TAG_GRPC]

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


app = FastAPI(
    title="Subscription Manager",
    description="Панель управления VPN-подписками через Xray gRPC",
    version="2026.1.0",
    lifespan=lifespan,
)

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


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Статус сервиса и подключения к Xray."""
    connected = False
    if xray_client:
        connected = xray_client.is_connected()
    return HealthResponse(
        status="online",
        version="2026.1.0",
        xray_connected=connected,
    )


@app.get("/stats", response_model=UserStats, dependencies=[Depends(verify_api_key)])
async def get_stats():
    """Статистика по пользователям."""
    return db.get_stats()


@app.get("/users", dependencies=[Depends(verify_api_key)])
async def list_users():
    """Список всех пользователей."""
    users = db.list_users()
    return {"users": users, "count": len(users)}


@app.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
)
async def create_user(data: UserCreate):
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
    )


@app.delete("/users/{email}", dependencies=[Depends(verify_api_key)])
async def delete_user(email: str):
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
)
async def get_user_links(email: str):
    """Получить все ссылки подписки для пользователя."""
    user = db.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    links = LinkGenerator.all_links(user["uuid"], email)
    return SubscriptionLinks(
        email=email,
        **links,
        all_links=list(links.values()),
    )


@app.get("/sub/{token}")
async def subscription_endpoint(token: str):
    """Публичный endpoint подписки (без API key).

    Клиент (Hiddify/Happ) использует этот URL для автоматического
    обновления конфигурации.
    """
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Subscription expired")

    text = LinkGenerator.subscription_text(user["uuid"], user["email"])
    return Response(
        content=text,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{user["email"]}.txt"',
            "Profile-Update-Interval": "12",
            "Subscription-UserInfo": "upload=0; download=0; total=0; expire=0",
        },
    )


@app.get(
    "/users/{email}/ips",
    dependencies=[Depends(verify_api_key)],
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
