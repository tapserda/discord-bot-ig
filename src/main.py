import asyncio
import discord
from discord.ext import commands, tasks
import aiohttp
import os
import json

# --- 1. KONFIGURASI (Environment Variables) ---
# Semua variable ini diambil dari tab 'Variables' di Railway agar data sensitif aman.
TOKEN = os.environ.get("DISCORD_TOKEN")          # Token Bot dari Discord Developer Portal
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")    # ID Server Discord tempat bot berada
CHANNEL_NAME = os.environ.get("DISCORD_CHANNEL_NAME") # Nama channel tujuan (contoh: 'ig-feed')
IG_USERNAME = os.environ.get("IG_USERNAME")      # Username Instagram yang mau dipantau
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")    # API Key dari dashboard RapidAPI

# File database lokal untuk menyimpan ID postingan yang sudah diproses
DATA_FILE = "seen_posts.json"

# --- 2. SISTEM PERSISTENCE (Penyimpanan Data) ---
def load_seen_posts():
    """Memuat daftar ID postingan yang sudah terkirim dari file JSON."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return set(json.load(f))
        except: pass
    return set()

def save_seen_posts(seen_set):
    """Menyimpan ID postingan baru ke file JSON agar tidak duplikat setelah restart."""
    with open(DATA_FILE, "w") as f:
        json.dump(list(seen_set), f)

# --- 3. LOGIKA UTAMA (Instagram Cog) ---
class InstagramForwarder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.username = IG_USERNAME
        self.seen_post_ids = load_seen_posts()
        # Menentukan apakah ini pertama kali bot dijalankan
        self.is_first_run = len(self.seen_post_ids) == 0
        self.instagram_task.start()

    async def get_latest_posts(self):
        """Mengambil data mentah dari RapidAPI Instagram Looter v2."""
        url = "https://instagram-looter2.p.rapidapi.com/web-profile" 
        querystring = {"username": self.username}
        
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": "instagram-looter2.p.rapidapi.com"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, params=querystring) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Mengakses struktur data spesifik Instagram Looter v2
                        user_data = data.get("data", {}).get("user", {})
                        media_edges = user_data.get("edge_owner_to_timeline_media", {}).get("edges", [])
                        
                        posts = []
                        for edge in media_edges[:12]:
                            node = edge.get("node", {})
                            
                            # Ekstraksi Caption
                            cap_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                            caption = cap_edges[0].get("node", {}).get("text", "") if cap_edges else ""

                            posts.append({
                                "id": node.get("id"),
                                "shortcode": node.get("shortcode"),
                                "image": node.get("display_url"),
                                "caption": caption,
                                "timestamp": node.get("taken_at_timestamp", 0)
                            })
                        
                        # SORTIR: Selalu letakkan timestamp terbesar (terbaru) di index 0
                        posts.sort(key=lambda x: x['timestamp'], reverse=True)
                        return posts
                    else:
                        print(f"❌ API Error: {response.status}")
            except Exception as e:
                print(f"❌ Connection Error: {e}")
        return []

    async def send_to_discord(self, post):
        """Memformat data Instagram menjadi Discord Embed yang cantik."""
        guild = self.bot.get_guild(int(GUILD_ID))
        if guild:
            channel = discord.utils.get(guild.channels, name=CHANNEL_NAME)
            if channel:
                link = f"https://www.instagram.com/p/{post['shortcode']}/"
                embed = discord.Embed(
                    title=f"New Content from @{self.username}",
                    description=post["caption"][:400] + ("..." if len(post["caption"]) > 400 else ""),
                    url=link,
                    color=0xbc2a8d # Warna khas Instagram
                )
                if post["image"]:
                    embed.set_image(url=post["image"])
                
                embed.set_footer(text="Instagram Forwarder by SAIKO SOCIETY")
                await channel.send(embed=embed)
                print(f"🚀 Forwarded: {post['shortcode']}")

    @tasks.loop(minutes=60)
    async def instagram_task(self):
        """Looping otomatis untuk mengecek postingan setiap 10 menit."""
        print(f"🔍 Memeriksa Instagram @{self.username}...")
        posts = await self.get_latest_posts()
        if not posts: return

        # Jika database kosong (First Run), tandai semua post lama sebagai 'sudah dilihat'
        if self.is_first_run:
            print("📦 Inisialisasi Database: Menandai post lama...")
            for post in posts:
                self.seen_post_ids.add(post["id"])
            save_seen_posts(self.seen_post_ids)
            self.is_first_run = False
            return

        # Cari postingan yang ID-nya belum ada di database seen_posts.json
        new_posts = [p for p in posts if p["id"] not in self.seen_post_ids]
        
        # Kirim post baru satu per satu (Urutan reversed agar post paling lama dikirim duluan)
        for post in reversed(new_posts):
            self.seen_post_ids.add(post["id"])
            save_seen_posts(self.seen_post_ids)
            await self.send_to_discord(post)

    @instagram_task.before_loop
    async def before_instagram_task(self):
        """Memastikan bot Discord sudah login sepenuhnya sebelum memulai loop."""
        await self.bot.wait_until_ready()

# --- 4. STARTUP BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot Online: {bot.user.name}")
    print(f"📡 Monitoring Akun: {IG_USERNAME}")

async def main():
    async with bot:
        await bot.add_cog(InstagramForwarder(bot))
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot dimatikan.")
                

