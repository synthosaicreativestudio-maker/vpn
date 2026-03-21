"""gRPC-клиент для управления пользователями Xray.

Использует HandlerService.AlterInbound для добавления / удаления
пользователей из VLESS-inbound'ов в рантайме (без перезагрузки).
"""

import logging
from typing import Optional

import grpc

logger = logging.getLogger("panel.xray")

# Ленивый импорт сгенерированных stubs ─────────────────────────
_stubs_loaded = False
_command_pb2 = None
_command_pb2_grpc = None
_user_pb2 = None
_serial_pb2 = None
_vless_pb2 = None


def _load_stubs():
    global _stubs_loaded, _command_pb2, _command_pb2_grpc
    global _user_pb2, _serial_pb2, _vless_pb2

    if _stubs_loaded:
        return

    try:
        from panel.proto import xray_command_pb2 as cmd
        from panel.proto import xray_command_pb2_grpc as cmd_grpc
        from panel.proto import xray_serial_pb2 as serial
        from panel.proto import xray_user_pb2 as user
        from panel.proto import xray_vless_pb2 as vless

        _command_pb2 = cmd
        _command_pb2_grpc = cmd_grpc
        _user_pb2 = user
        _serial_pb2 = serial
        _vless_pb2 = vless
        _stubs_loaded = True
        logger.info("gRPC stubs loaded successfully")
    except ImportError as exc:
        logger.error(
            "gRPC stubs not found. Run: cd panel/proto && bash generate.sh"
        )
        raise RuntimeError(
            "Proto stubs not generated. "
            "Run: cd panel/proto && bash generate.sh"
        ) from exc


class XrayClient:
    """Клиент для Xray HandlerService gRPC API."""

    def __init__(self, grpc_host: str):
        _load_stubs()
        self.channel = grpc.insecure_channel(grpc_host)
        self.handler = _command_pb2_grpc.HandlerServiceStub(self.channel)
        self._host = grpc_host
        logger.info("XrayClient connected to %s", grpc_host)

    # ── Public API ────────────────────────────────────────────

    def add_user(
        self,
        inbound_tag: str,
        email: str,
        uuid: str,
        flow: str = "",
    ) -> bool:
        """Добавить пользователя в указанный inbound."""
        try:
            account = _vless_pb2.Account(id=uuid, flow=flow)

            user = _user_pb2.User(
                email=email,
                account=_serial_pb2.TypedMessage(
                    type="xray.proxy.vless.Account",
                    value=account.SerializeToString(),
                ),
            )

            operation = _command_pb2.AddUserOperation(user=user)

            request = _command_pb2.AlterInboundRequest(
                tag=inbound_tag,
                operation=_serial_pb2.TypedMessage(
                    type="xray.app.proxyman.command.AddUserOperation",
                    value=operation.SerializeToString(),
                ),
            )

            self.handler.AlterInbound(request)
            logger.info("User %s added to inbound %s", email, inbound_tag)
            return True

        except grpc.RpcError as exc:
            logger.error(
                "Failed to add user %s: %s", email, exc.details()
            )
            return False

    def remove_user(self, inbound_tag: str, email: str) -> bool:
        """Удалить пользователя из указанного inbound."""
        try:
            operation = _command_pb2.RemoveUserOperation(email=email)

            request = _command_pb2.AlterInboundRequest(
                tag=inbound_tag,
                operation=_serial_pb2.TypedMessage(
                    type="xray.app.proxyman.command.RemoveUserOperation",
                    value=operation.SerializeToString(),
                ),
            )

            self.handler.AlterInbound(request)
            logger.info(
                "User %s removed from inbound %s", email, inbound_tag
            )
            return True

        except grpc.RpcError as exc:
            logger.error(
                "Failed to remove user %s: %s", email, exc.details()
            )
            return False

    def add_user_all_inbounds(
        self, email: str, uuid: str, inbound_tags: list[str]
    ) -> dict[str, bool]:
        """Добавить пользователя во все указанные inbound'ы."""
        results = {}
        for tag in inbound_tags:
            # Vision требует flow, остальные — нет
            flow = "xtls-rprx-vision" if "Vision" in tag else ""
            results[tag] = self.add_user(tag, email, uuid, flow)
        return results

    def remove_user_all_inbounds(
        self, email: str, inbound_tags: list[str]
    ) -> dict[str, bool]:
        """Удалить пользователя из всех inbound'ов."""
        results = {}
        for tag in inbound_tags:
            results[tag] = self.remove_user(tag, email)
        return results

    def get_inbound_users(
        self, inbound_tag: str
    ) -> Optional[list[dict]]:
        """Получить список пользователей inbound'а."""
        try:
            request = _command_pb2.GetInboundUserRequest(tag=inbound_tag)
            response = self.handler.GetInboundUsers(request)
            return [
                {"email": u.email, "level": u.level}
                for u in response.users
            ]
        except grpc.RpcError as exc:
            logger.error(
                "Failed to get users for %s: %s",
                inbound_tag,
                exc.details(),
            )
            return None

    def is_connected(self) -> bool:
        """Проверка доступности Xray gRPC."""
        try:
            grpc.channel_ready_future(self.channel).result(timeout=2)
            return True
        except grpc.FutureTimeoutError:
            return False

    def close(self):
        """Закрытие gRPC канала."""
        self.channel.close()
