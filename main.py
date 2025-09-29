import os
import subprocess
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def run_cmd(cmd):
    return subprocess.getoutput(cmd)


async def cmd_ps(message: types.Message):
    if message.from_user.id != ALLOWED_USER_ID:
        return await message.answer("⛔ Нет доступа")
    result = run_cmd("docker ps --format '{{.Names}} - {{.Status}}'")
    await message.answer(f"📦 Контейнеры:\n{result or 'Нет запущенных'}")


async def cmd_stop(message: types.Message):
    if message.from_user.id != ALLOWED_USER_ID:
        return await message.answer("⛔ Нет доступа")
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("❌ Используй: /stop <container>")
    container = args[1]
    result = run_cmd(f"docker stop {container}")
    await message.answer(f"🛑 Остановлен: {result}")


async def cmd_start(message: types.Message):
    if message.from_user.id != ALLOWED_USER_ID:
        return await message.answer("⛔ Нет доступа")
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("❌ Используй: /start <container>")
    container = args[1]
    result = run_cmd(f"docker start {container}")
    await message.answer(f"▶️ Запущен: {result}")


async def cmd_restart(message: types.Message):
    if message.from_user.id != ALLOWED_USER_ID:
        return await message.answer("⛔ Нет доступа")
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("❌ Используй: /restart <container>")
    container = args[1]
    result = run_cmd(f"docker restart {container}")
    await message.answer(f"🔄 Перезапущен: {result}")


async def main():
    dp.message.register(cmd_ps, Command("ps"))
    dp.message.register(cmd_stop, Command("stop"))
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_restart, Command("restart"))

    print("🚀 Бот запущен и ждёт команды...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
