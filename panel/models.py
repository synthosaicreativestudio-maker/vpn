"""Pydantic-модели для API запросов и ответов."""

import uuid as uuid_lib
from typing import List, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Создание нового пользователя."""

    email: str = Field(..., description="Уникальный email или имя пользователя")
    uuid: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        description="UUID пользователя (VLESS/Reality)",
    )
    ip_limit: int = Field(
        default=2, ge=1, le=10, description="Лимит одновременных IP"
    )
    expire_days: Optional[int] = Field(
        default=None, description="Срок действия в днях (пропустить для бессрочного)"
    )
    description: Optional[str] = Field(None, description="Заметка о пользователе")


class UserResponse(BaseModel):
    """Информация о пользователе."""

    email: str
    uuid: str
    ip_limit: int
    created_at: str
    expires_at: Optional[str]
    is_active: bool
    sub_token: str


class SubscriptionLinks(BaseModel):
    """Ссылки подписки для всех протоколов."""

    email: str
    vless_reality: str
    vless_xhttp: str
    vless_grpc: str
    shadow_tls: str
    tuic: str
    hysteria2: str
    all_links: List[str]


class UserStats(BaseModel):
    """Статистика по пользователям."""

    total_users: int
    active_users: int
    expired_users: int


class HealthResponse(BaseModel):
    """Статус сервиса."""

    status: str
    version: str
    xray_connected: bool
