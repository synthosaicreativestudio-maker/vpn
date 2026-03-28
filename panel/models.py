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


class UserUpdate(BaseModel):
    """Обновление данных пользователя (все поля опциональны)."""

    ip_limit: Optional[int] = Field(None, ge=1, le=10, description="Лимит одновременных IP")
    expires_at: Optional[str] = Field(None, description="Дата истечения (ISO 8601) или null для бессрочного")
    is_active: Optional[bool] = Field(None, description="Активность подписки")
    description: Optional[str] = Field(None, description="Заметка о пользователе")
    expire_days: Optional[int] = Field(None, ge=1, description="Добавить N дней к сроку действия")
    phone: Optional[str] = Field(None, description="Номер телефона пользователя")
    total_gb: Optional[float] = Field(None, ge=0, description="Лимит трафика в Гб")
    used_gb: Optional[float] = Field(None, ge=0, description="Использованный трафик в Гб")


class UserResponse(BaseModel):
    """Информация о пользователе."""

    email: str
    uuid: str
    ip_limit: int
    created_at: str
    expires_at: Optional[str]
    is_active: bool
    sub_token: str
    phone: Optional[str] = None
    total_gb: float = 0
    used_gb: float = 0


class SubscriptionLinks(BaseModel):
    """Ссылки подписки для всех протоколов."""

    email: str
    sub_url: str
    vless_reality: str
    vless_xhttp: str
    vless_grpc: str
    vless_ws: str
    hysteria2: str
    yandex_bridge: str = ""
    yandex_bridge_ws: str = ""
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
