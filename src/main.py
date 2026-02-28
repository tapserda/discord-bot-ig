import discord
from discord.ext import commands
import os
import asyncio

# Mengambil Token dari Environment Variables Railway
TOKEN = os.environ.get("DISCORD_TOKEN")

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Memuat modul instagram.py
        await self.load_extension("instagram")
        print("✅ Extension Instagram berhasil dimuat!")

    async def on_ready(self):
        print(f"🚀 Logged in as: {self.user} (ID: {self.user.id})")
        print("--- Bot is running 24/7 on Railway ---")

async def main():
    bot = MyBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

