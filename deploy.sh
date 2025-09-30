#!/bin/bash
set -e

# Корень проекта (так как скрипт лежит в корне)
PROJECT_ROOT="$(dirname "$0")"

# Загружаем переменные из .env
if [ -f "${PROJECT_ROOT}/.env" ]; then
  export $(grep -v '^#' "${PROJECT_ROOT}/.env" | xargs)
else
  echo "❌ Файл .env не найден в корне проекта (${PROJECT_ROOT}/.env)"
  exit 1
fi

: "${MY_APP:?❌ Не задан MY_APP в .env}"
: "${REMOTE_USER:?❌ Не задан REMOTE_USER в .env}"
: "${REMOTE_HOST:?❌ Не задан REMOTE_HOST в .env}"

REMOTE_DIR="/root/${MY_APP}"
IMAGE_NAME="${MY_APP}:latest"
CONTAINER_NAME=${MY_APP}

echo "🚀 Деплой бота на ${REMOTE_USER}@${REMOTE_HOST}..."

# 1. Синхронизируем проект
rsync -avz --progress --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  "${PROJECT_ROOT}/" ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}

# 2. Собираем образ
ssh ${REMOTE_USER}@${REMOTE_HOST} "
  cd ${REMOTE_DIR} && \
  docker build -t ${IMAGE_NAME} .
"

# 3. Перезапускаем контейнер
ssh ${REMOTE_USER}@${REMOTE_HOST} "
  cd ${REMOTE_DIR} && \
  docker rm -f ${CONTAINER_NAME} 2>/dev/null || true && \
  docker run -d --name ${CONTAINER_NAME} \
    --restart unless-stopped \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --env-file .env \
    ${IMAGE_NAME}
"

echo "✅ Деплой завершён!"
