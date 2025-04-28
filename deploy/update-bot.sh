#!/usr/bin/env bash
# Обновляет репозиторий и перезапускает systemd-сервис бота
set -euo pipefail

REPO_DIR="/root/target-assistant-bot"
SERVICE_NAME="targetbot.service"

cd "$REPO_DIR"

# Получаем последние изменения
if git pull --ff-only; then
    echo "[update-bot] Репозиторий обновлён. Перезапуск службы $SERVICE_NAME"
    sudo systemctl restart "$SERVICE_NAME"
else
    echo "[update-bot] git pull завершился с ошибкой" >&2
    exit 1
fi 