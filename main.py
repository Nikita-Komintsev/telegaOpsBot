import os
import asyncio
import docker
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Docker клиент
docker_client = docker.from_env()

MAX_LOG_MESSAGE_LEN = 4000  # запас под лимит Telegram


# ---------- Docker helpers ----------

def get_containers():
    """Список всех контейнеров (имя, статус)."""
    containers = docker_client.containers.list(all=True)
    return [(c.name, c.status) for c in containers]


def stop_container(name: str) -> str:
    container = docker_client.containers.get(name)
    container.stop()
    return f"🛑 Контейнер {name} остановлен"


def start_container(name: str) -> str:
    container = docker_client.containers.get(name)
    container.start()
    return f"▶️ Контейнер {name} запущен"


def restart_container(name: str) -> str:
    container = docker_client.containers.get(name)
    container.restart()
    return f"🔄 Контейнер {name} перезапущен"


def get_logs(name: str, tail: int = 100, offset: int = 0) -> list[str]:
    """
    Возвращает список частей логов контейнера.
    tail — сколько строк взять за раз, offset — сколько уже показано ранее.
    """
    container = docker_client.containers.get(name)
    all_logs = container.logs().decode(errors="ignore").splitlines()

    if offset >= len(all_logs):
        return [f"📜 Логи {name}:\n(больше нет строк)"]

    start_index = max(len(all_logs) - offset - tail, 0)
    selected_logs = all_logs[start_index : len(all_logs) - offset]
    logs = "\n".join(selected_logs)

    header = (
        f"📜 Логи {name} "
        f"(строки {len(all_logs) - len(selected_logs) - offset}–{len(all_logs) - offset} из {len(all_logs)}):\n\n"
    )

    parts = []
    current = ""
    for line in logs.splitlines():
        if len(current) + len(line) + 1 > MAX_LOG_MESSAGE_LEN:
            parts.append(current)
            current = ""
        current += line + "\n"
    if current:
        parts.append(current)

    if parts:
        parts[0] = header + parts[0]
    else:
        parts = [header + "(пусто)"]

    return parts


# ---------- Telegram Handlers ----------

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start."""
    if message.from_user.id != ALLOWED_USER_ID:
        return await message.answer("⛔ Нет доступа")
    await show_containers(message)


async def show_containers(message: types.Message):
    """Показать список контейнеров."""
    containers = get_containers()
    if not containers:
        return await message.answer("❌ Нет контейнеров")

    kb = InlineKeyboardBuilder()
    for name, status in containers:
        kb.button(text=f"{name} ({status})", callback_data=f"select:{name}")
    kb.button(text="🔄 Обновить", callback_data="refresh")
    kb.adjust(1)

    try:
        await message.edit_text("📦 Выбери контейнер:", reply_markup=kb.as_markup())
    except Exception:
        await message.answer("📦 Выбери контейнер:", reply_markup=kb.as_markup())


@dp.callback_query(lambda c: c.data == "refresh")
async def refresh_list(callback: types.CallbackQuery):
    """Обновить список контейнеров."""
    await callback.answer("🔄 Обновляю...")
    await show_containers(callback.message)


@dp.callback_query(lambda c: c.data.startswith("select:"))
async def container_selected(callback: types.CallbackQuery):
    """Меню действий для выбранного контейнера."""
    name = callback.data.split(":", 1)[1]

    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Запустить", callback_data=f"action:start:{name}")
    kb.button(text="🛑 Остановить", callback_data=f"action:stop:{name}")
    kb.button(text="🔄 Перезапустить", callback_data=f"action:restart:{name}")
    kb.button(text="📜 Логи", callback_data=f"action:logs:{name}")
    kb.button(text="⬅️ Назад", callback_data="refresh")
    kb.adjust(2)

    try:
        await callback.message.edit_text(
            f"Что сделать с контейнером <b>{name}</b>?",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            f"Что сделать с контейнером <b>{name}</b>?",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("action:"))
async def container_action(callback: types.CallbackQuery):
    """Обработка действий с контейнером."""
    _, action, name = callback.data.split(":", 2)
    try:
        if action == "start":
            result = start_container(name)
            parse_mode = None
        elif action == "stop":
            result = stop_container(name)
            parse_mode = None
        elif action == "restart":
            result = restart_container(name)
            parse_mode = None
        elif action == "logs":
            log_parts = get_logs(name, tail=100, offset=0)
            for part in log_parts:
                await callback.message.answer(f"```\n{part}\n```", parse_mode="Markdown")

            # Кнопки для логов (новое сообщение)
            kb = InlineKeyboardBuilder()
            kb.button(text="📜 Показать ещё", callback_data=f"logs_more:{name}:100")
            kb.button(text="⬅️ Назад", callback_data="refresh")
            kb.adjust(1)
            await callback.message.answer("Что дальше?", reply_markup=kb.as_markup())

            await callback.answer()
            return  # не показываем контейнеры после логов
        else:
            result = "❌ Неизвестное действие"
            parse_mode = None
    except Exception as e:
        result = f"⚠️ Ошибка: {e}"
        parse_mode = None

    # редактируем текущее сообщение, а не отправляем новое
    try:
        await callback.message.edit_text(result, parse_mode=parse_mode)
    except Exception:
        await callback.message.answer(result, parse_mode=parse_mode)

    await callback.answer()
    await show_containers(callback.message)


@dp.callback_query(lambda c: c.data.startswith("logs_more:"))
async def logs_more(callback: types.CallbackQuery):
    """Догрузка дополнительных строк логов (новые сообщения)."""
    _, name, offset_str = callback.data.split(":")
    offset = int(offset_str)

    log_parts = get_logs(name, tail=100, offset=offset)
    for part in log_parts:
        await callback.message.answer(f"```\n{part}\n```", parse_mode="Markdown")

    new_offset = offset + 100
    kb = InlineKeyboardBuilder()
    kb.button(text="📜 Ещё +100 строк", callback_data=f"logs_more:{name}:{new_offset}")
    kb.button(text="⬅️ Назад", callback_data="refresh")
    kb.adjust(1)
    await callback.message.answer("Что дальше?", reply_markup=kb.as_markup())

    await callback.answer()


# ---------- Main ----------

async def main():
    print("🚀 Бот запущен и ждёт команды...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
