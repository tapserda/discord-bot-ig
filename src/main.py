import asyncio
import discord
from discord.ext import commands, tasks
import aiohttp
import os

# --- 1. AMBIL DATA DARI RAILWAY VARIABLES ---
# Nama variabel di bawah ini harus persis dengan yang ada di image_8b7cab.png
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
CHANNEL_NAME = os.environ.get("DISCORD_CHANNEL_NAME")
IG_USERNAME = os.environ.get("IG_USERNAME")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

# --- 2. INSTAGRAM COG CLASS ---
class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = RAPIDAPI_KEY 
        self.username = IG_USERNAME
        self.last_post_id = None
        self.instagram_task.start()

    def cog_unload(self):
        self.instagram_task.cancel()

    async def get_latest_post(self):
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
                        result = data.get("result", {})
                        edges = result.get("edges", [])
                        
                        if edges:
                            node = edges[0].get("node", {})
                            cap_data = node.get("caption", {})
                            text = cap_data.get("text", "No caption provided.")
                            
                            img_url = node.get("display_url")
                            if not img_url:
                                candidates = node.get("image_versions2", {}).get("candidates", [])
                                if candidates:
                                    img_url = candidates[0].get("url")

                            return {
                                "id": node.get("id"),
                                "shortcode": node.get("code"),
                                "image": img_url,
                                "caption": text
                            }
                    else:
                        print(f"API Error: {response.status}")
            except Exception as e:
                print(f"Error Request IG: {e}")
        return None
    
    @tasks.loop(minutes=10) # Sesuai permintaan kamu: Cek tiap 10 menit
    async def instagram_task(self):
        post_data = await self.get_latest_post()
        if post_data:
            # Log debug biar kamu bisa pantau di Railway Dashboard
            print(f"DEBUG: ID API: {post_data['id']} | Last Sent ID: {self.last_post_id}")
            
            if self.last_post_id != post_data["id"]:
                self.last_post_id = post_data["id"] 
                
                # Pastikan GUILD_ID dan CHANNEL_NAME sudah diisi di Railway
                guild = self.bot.get_guild(int(GUILD_ID))
                if guild:
                    channel = discord.utils.get(guild.channels, name=CHANNEL_NAME)
                    if channel:
                        link = f"https://www.instagram.com/p/{post_data['shortcode']}/"
                        embed = discord.Embed(
                            title=f"New Post from @{self.username}",
                            description=post_data["caption"][:300],
                            url=link,
                            color=0xbc2a8d
                        )
                        if post_data["image"]:
                            embed.set_image(url=post_data["image"])
                        
                        embed.set_footer(text="Instagram Forwarder by SAIKO SOCIETY")
                        await channel.send(embed=embed)
                        print(f"🚀 Berhasil kirim post: {post_data['shortcode']}")

    @instagram_task.before_loop
    async def before_instagram_task(self):
        await self.bot.wait_until_ready()

# --- 3. BOT INITIALIZATION ---
intents = discord.Intents.default()
intents.guilds = True 
intents.members = True 
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as: {bot.user.name}")
    print(f"🔗 Connected to {len(bot.guilds)} guilds.")

# --- 4. MAIN RUNNER ---
async def main():
    async with bot:
        await bot.add_cog(Instagram(bot))
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot dimatikan.")
