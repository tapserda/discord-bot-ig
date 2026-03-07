import asyncio
import discord
from discord.ext import commands, tasks
import aiohttp
import os
import json

# --- 1. CONFIGURATION (RAILWAY VARIABLES) ---
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
CHANNEL_NAME = os.environ.get("DISCORD_CHANNEL_NAME")
IG_USERNAME = os.environ.get("IG_USERNAME")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

DATA_FILE = "seen_posts.json"

# --- 2. PERSISTENCE LAYER ---
def load_seen_posts():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Error loading JSON: {e}")
    return set()

def save_seen_posts(seen_set):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(list(seen_set), f)
    except Exception as e:
        print(f"Error saving JSON: {e}")

# --- 3. INSTAGRAM COG ---
class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = RAPIDAPI_KEY 
        self.username = IG_USERNAME
        self.seen_post_ids = load_seen_posts()
        self.is_first_run = len(self.seen_post_ids) == 0
        self.instagram_task.start()

    def cog_unload(self):
        self.instagram_task.cancel()

    async def get_latest_posts(self):
        url = "https://instagram120.p.rapidapi.com/api/instagram/posts"
        payload = {"username": self.username, "maxId": ""}
        headers = {
            "content-type": "application/json",
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "instagram120.p.rapidapi.com"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        edges = data.get("result", {}).get("edges", [])
                        
                        posts = []
                        # Scan 12 post teratas untuk melewati Pinned Posts & Reels lama
                        for edge in edges[:12]:
                            node = edge.get("node", {})
                            
                            # Deteksi thumbnail/gambar
                            img_url = node.get("display_url")
                            if not img_url:
                                candidates = node.get("image_versions2", {}).get("candidates", [])
                                if candidates:
                                    img_url = candidates[0].get("url")

                            posts.append({
                                "id": node.get("id"),
                                "shortcode": node.get("code"),
                                "image": img_url,
                                "caption": node.get("caption", {}).get("text", "No caption.")
                            })
                        return posts
                    else:
                        print(f"API Error: {response.status}")
            except Exception as e:
                print(f"Request Error: {e}")
        return []
    
    @tasks.loop(minutes=10)
    async def instagram_task(self):
        posts = await self.get_latest_posts()
        if not posts:
            return

        # Jika baru pertama kali jalan, catat semua yang ada agar tidak spam
        if self.is_first_run:
            for post in posts:
                if post["id"]:
                    self.seen_post_ids.add(post["id"])
            save_seen_posts(self.seen_post_ids)
            self.is_first_run = False
            print(f"✅ Database diinisialisasi. Menunggu post baru dari @{self.username}...")
            return

        # Cari postingan yang benar-benar baru
        new_posts = []
        for post in posts:
            if post["id"] and post["id"] not in self.seen_post_ids:
                new_posts.append(post)

        # Kirim ke Discord (reversed agar urutan waktu benar)
        for post in reversed(new_posts):
            self.seen_post_ids.add(post["id"])
            save_seen_posts(self.seen_post_ids)
            
            guild = self.bot.get_guild(int(GUILD_ID))
            if guild:
                channel = discord.utils.get(guild.channels, name=CHANNEL_NAME)
                if channel:
                    link = f"https://www.instagram.com/p/{post['shortcode']}/"
                    embed = discord.Embed(
                        title=f"New Content from @{self.username}",
                        description=post["caption"][:400] + "...",
                        url=link,
                        color=0xbc2a8d
                    )
                    if post["image"]:
                        embed.set_image(url=post["image"])
                    embed.set_footer(text="Instagram Forwarder by SAIKO SOCIETY")
                    
                    await channel.send(embed=embed)
                    print(f"🚀 Sent to Discord: {post['shortcode']}")

    @instagram_task.before_loop
    async def before_instagram_task(self):
        await self.bot.wait_until_ready()

# --- 4. BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot Online: {bot.user.name}")

async def main():
    async with bot:
        await bot.add_cog(Instagram(bot))
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot Offline.")
