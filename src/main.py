import asyncio
import discord
from discord.ext import commands, tasks
import aiohttp
import os
import json

# --- 1. CONFIGURATION ---
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
CHANNEL_NAME = os.environ.get("DISCORD_CHANNEL_NAME")
IG_USERNAME = os.environ.get("IG_USERNAME")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

DATA_FILE = "seen_posts.json"

# --- 2. PERSISTENCE ---
def load_seen_posts():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return set(json.load(f))
        except: pass
    return set()

def save_seen_posts(seen_set):
    with open(DATA_FILE, "w") as f:
        json.dump(list(seen_set), f)

# --- 3. INSTAGRAM COG ---
class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.username = IG_USERNAME
        self.seen_post_ids = load_seen_posts()
        self.is_first_run = len(self.seen_post_ids) == 0
        self.instagram_task.start()

    async def get_latest_posts(self):
        # ENDPOINT SESUAI STRUKTUR BARU
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
                        # Struktur Instagram Looter: data -> user -> edge_owner_to_timeline_media
                        user_data = data.get("data", {}).get("user", {})
                        media_edges = user_data.get("edge_owner_to_timeline_media", {}).get("edges", [])
                        
                        posts = []
                        for edge in media_edges[:12]:
                            node = edge.get("node", {})
                            
                            # Mengambil caption
                            cap_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                            caption = cap_edges[0].get("node", {}).get("text", "") if cap_edges else ""

                            posts.append({
                                "id": node.get("id"),
                                "shortcode": node.get("shortcode"),
                                "image": node.get("display_url"),
                                "caption": caption,
                                "timestamp": node.get("taken_at_timestamp", 0) # Penting untuk sortir waktu
                            })
                        
                        # SORTIR BERDASARKAN WAKTU (Agar Post 2022 tidak muncul duluan)
                        posts.sort(key=lambda x: x['timestamp'], reverse=True)
                        return posts
                    else:
                        print(f"❌ API Error: {response.status}")
            except Exception as e:
                print(f"❌ Request Error: {e}")
        return []

    async def send_to_discord(self, post):
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
                print(f"🚀 Terkirim ke Discord: {post['shortcode']}")

    @tasks.loop(minutes=10)
    async def instagram_task(self):
        print(f"🔍 Checking @{self.username}...")
        posts = await self.get_latest_posts()
        if not posts: return

        if self.is_first_run:
            print("📦 Inisialisasi Database...")
            for post in posts:
                self.seen_post_ids.add(post["id"])
            save_seen_posts(self.seen_post_ids)
            self.is_first_run = False
            
            # Tes kirim 1 post yang benar-benar TERBARU secara waktu
            if posts:
                print(f"🧪 Mengirim post terbaru sebagai tes...")
                await self.send_to_discord(posts[0])
            return

        new_posts = [p for p in posts if p["id"] not in self.seen_post_ids]
        for post in reversed(new_posts):
            self.seen_post_ids.add(post["id"])
            save_seen_posts(self.seen_post_ids)
            await self.send_to_discord(post)

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
    asyncio.run(main())
