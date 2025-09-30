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


def get_logs(name: str, tail: int = 35) -> str:
    container = docker_client.containers.get(name)
    logs = container.logs(tail=tail).decode(errors="ignore")
    return f"📜 Логи {name}:\n```\n{logs}\n```"


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != ALLOWED_USER_ID:
        return await message.answer("⛔ Нет доступа")
    await show_containers(message)


async def show_containers(message: types.Message):
    containers = get_containers()
    if not containers:
        return await message.answer("❌ Нет контейнеров")

    kb = InlineKeyboardBuilder()
    for name, status in containers:
        kb.button(text=f"{name} ({status})", callback_data=f"select:{name}")
    kb.adjust(1)
    await message.answer("📦 Выбери контейнер:", reply_markup=kb.as_markup())


@dp.callback_query(lambda c: c.data.startswith("select:"))
async def container_selected(callback: types.CallbackQuery):
    name = callback.data.split(":", 1)[1]

    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Запустить", callback_data=f"action:start:{name}")
    kb.button(text="🛑 Остановить", callback_data=f"action:stop:{name}")
    kb.button(text="🔄 Перезапустить", callback_data=f"action:restart:{name}")
    kb.button(text="📜 Логи", callback_data=f"action:logs:{name}")
    kb.adjust(2)

    await callback.message.answer(
        f"Что сделать с контейнером <b>{name}</b>?",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("action:"))
async def container_action(callback: types.CallbackQuery):
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
            result = get_logs(name)
            parse_mode = "Markdown"
        else:
            result = "❌ Неизвестное действие"
            parse_mode = None
    except Exception as e:
        result = f"⚠️ Ошибка: {e}"
        parse_mode = None

    # Отправляем результат действия
    await callback.message.answer(result, parse_mode=parse_mode)
    await callback.answer()

    # После любого действия показываем список контейнеров
    await show_containers(callback.message)



async def main():
    print("🚀 Бот запущен и ждёт команды...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
