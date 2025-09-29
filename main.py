import os
import subprocess
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def run_cmd(cmd):
    return subprocess.getoutput(cmd)


def get_containers():
    result = run_cmd("docker ps -a --format '{{.Names}} - {{.Status}}'")
    containers = []
    for line in result.splitlines():
        if line.strip():
            name, status = line.split(" - ", 1)
            containers.append((name, status))
    return containers


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != ALLOWED_USER_ID:
        return await message.answer("⛔ Нет доступа")
    await show_containers(message)


async def show_containers(message: types.Message):
    containers = get_containers()
    if not containers:
        return await message.answer("❌ Контейнеров не найдено")

    kb = InlineKeyboardBuilder()
    for name, status in containers:
        kb.button(text=f"{name} ({status})", callback_data=f"container:{name}")
    kb.adjust(1)

    await message.answer("📦 Выбери контейнер:", reply_markup=kb.as_markup())


@dp.callback_query(lambda c: c.data.startswith("container:"))
async def container_menu(callback: types.CallbackQuery):
    container = callback.data.split(":", 1)[1]

    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Запустить", callback_data=f"action:start:{container}")
    kb.button(text="🛑 Остановить", callback_data=f"action:stop:{container}")
    kb.button(text="🔄 Перезапустить", callback_data=f"action:restart:{container}")
    kb.button(text="📜 Логи", callback_data=f"action:logs:{container}")
    kb.button(text="🔙 Назад", callback_data="back")
    kb.adjust(2, 2, 1)

    await callback.message.edit_text(
        f"⚙️ Контейнер: `{container}`\nВыбери действие:",
        parse_mode="Markdown",
        reply_markup=kb.as_markup(),
    )


@dp.callback_query(lambda c: c.data == "back")
async def back_to_list(callback: types.CallbackQuery):
    await show_containers(callback.message)


@dp.callback_query(lambda c: c.data.startswith("action:"))
async def container_action(callback: types.CallbackQuery):
    _, action, container = callback.data.split(":", 2)

    if action == "start":
        result = run_cmd(f"docker start {container}")
        text = f"▶️ Запущен: `{result}`"
    elif action == "stop":
        result = run_cmd(f"docker stop {container}")
        text = f"🛑 Остановлен: `{result}`"
    elif action == "restart":
        result = run_cmd(f"docker restart {container}")
        text = f"🔄 Перезапущен: `{result}`"
    elif action == "logs":
        result = run_cmd(f"docker logs --tail 20 {container}")
        text = f"📜 Логи контейнера `{container}`:\n```\n{result}\n```"
    else:
        text = "❌ Неизвестное действие"

    await callback.message.edit_text(
        text, parse_mode="Markdown", reply_markup=None
    )


async def main():
    print("🚀 Бот запущен и ждёт команды...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
