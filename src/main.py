import asyncio
import discord
from discord.ext import commands, tasks
import aiohttp
import os
import json

# --- 1. AMBIL DATA DARI RAILWAY VARIABLES ---
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
CHANNEL_NAME = os.environ.get("DISCORD_CHANNEL_NAME")
IG_USERNAME = os.environ.get("IG_USERNAME")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

# --- 2. SISTEM PENYIMPANAN DATA (PERSISTENCE) ---
DATA_FILE = "seen_posts.json"

def load_seen_posts():
    """Membaca ID post yang sudah tersimpan dari file JSON."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Error membaca file JSON: {e}")
    return set()

def save_seen_posts(seen_set):
    """Menyimpan ID post baru ke file JSON."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(list(seen_set), f)
    except Exception as e:
        print(f"Error menyimpan file JSON: {e}")

# --- 3. INSTAGRAM COG CLASS ---
class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = RAPIDAPI_KEY 
        self.username = IG_USERNAME
        
        # Load ID dari file saat bot menyala
        self.seen_post_ids = load_seen_posts() 
        # Jika file kosong (baru pertama kali banget jalan), set True
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
                        # Ambil 5 post teratas untuk melewati Pinned Posts
                        for edge in edges[:5]:
                            node = edge.get("node", {})
                            cap_data = node.get("caption", {})
                            text = cap_data.get("text", "No caption provided.")
                            
                            img_url = node.get("display_url")
                            if not img_url:
                                candidates = node.get("image_versions2", {}).get("candidates", [])
                                if candidates:
                                    img_url = candidates[0].get("url")

                            posts.append({
                                "id": node.get("id"),
                                "shortcode": node.get("code"),
                                "image": img_url,
                                "caption": text
                            })
                        return posts
                    else:
                        print(f"API Error: {response.status}")
            except Exception as e:
                print(f"Error Request IG: {e}")
        return []
    
    @tasks.loop(minutes=10)
    async def instagram_task(self):
        posts = await self.get_latest_posts()
        
        if not posts:
            return

        # Saat bot benar-benar pertama kali nyala (file JSON kosong)
        if self.is_first_run:
            for post in posts:
                if post["id"]:
                    self.seen_post_ids.add(post["id"])
            save_seen_posts(self.seen_post_ids) # Simpan ke file
            self.is_first_run = False
            print(f"DEBUG: First run. Mengingat {len(self.seen_post_ids)} post awal ke JSON.")
            return

        # Cek post baru dari urutan bawah ke atas
        for post in reversed(posts):
            if post["id"] and post["id"] not in self.seen_post_ids:
                # Ditemukan post baru!
                self.seen_post_ids.add(post["id"])
                save_seen_posts(self.seen_post_ids) # Update file JSON dengan ID baru
                print(f"DEBUG: Post baru terdeteksi: {post['shortcode']}")
                
                guild = self.bot.get_guild(int(GUILD_ID))
                if guild:
                    channel = discord.utils.get(guild.channels, name=CHANNEL_NAME)
                    if channel:
                        link = f"https://www.instagram.com/p/{post['shortcode']}/"
                        embed = discord.Embed(
                            title=f"New Post from @{self.username}",
                            description=post["caption"][:300],
                            url=link,
                            color=0xbc2a8d
                        )
                        if post["image"]:
                            embed.set_image(url=post["image"])
                        
                        embed.set_footer(text="Instagram Forwarder by SAIKO SOCIETY")
                        await channel.send(embed=embed)
                        print(f"🚀 Berhasil kirim post: {post['shortcode']}")

    @instagram_task.before_loop
    async def before_instagram_task(self):
        await self.bot.wait_until_ready()

# --- 4. BOT INITIALIZATION ---
intents = discord.Intents.default()
intents.guilds = True 
intents.members = True 
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as: {bot.user.name}")
    print(f"🔗 Connected to {len(bot.guilds)} guilds.")

# --- 5. MAIN RUNNER ---
async def main():
    async with bot:
        await bot.add_cog(Instagram(bot))
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot dimatikan.")
        
