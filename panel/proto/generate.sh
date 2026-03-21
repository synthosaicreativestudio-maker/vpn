#!/bin/bash
# Генерация Python gRPC stubs из .proto файлов
# Запуск: cd panel/proto && bash generate.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🔧 Генерация gRPC stubs..."

python -m grpc_tools.protoc \
    --proto_path="$SCRIPT_DIR" \
    --python_out="$SCRIPT_DIR" \
    --grpc_python_out="$SCRIPT_DIR" \
    "$SCRIPT_DIR/xray_serial.proto" \
    "$SCRIPT_DIR/xray_user.proto" \
    "$SCRIPT_DIR/xray_vless.proto" \
    "$SCRIPT_DIR/xray_command.proto"

# Правим импорты для работы как модуль Python-пакета
for f in "$SCRIPT_DIR"/*_pb2*.py; do
    if [ -f "$f" ]; then
        sed -i '' 's/^import xray_/from panel.proto import xray_/g' "$f" 2>/dev/null || \
        sed -i 's/^import xray_/from panel.proto import xray_/g' "$f"
    fi
done

echo "✅ Готово! Сгенерированы файлы:"
ls -la "$SCRIPT_DIR"/*_pb2*.py
