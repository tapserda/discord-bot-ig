import asyncio
import discord
from discord.ext import commands, tasks
import aiohttp
import yaml
import os

# --- 1. LOAD CONFIGURATION ---
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# --- 2. INSTAGRAM COG CLASS ---
class Instagram(commands.Cog):
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        # API Key dari RapidAPI kamu
        self.api_key = "717715efd1mshccccabe747e34e3p1dd701jsn638bbcfd2619" 
        self.username = config["INSTAGRAM"]["USERNAME"]
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
                            
                            # Ambil Caption
                            cap_data = node.get("caption", {})
                            text = cap_data.get("text", "No caption provided.")
                            
                            # Ambil Foto
                            img_url = node.get("display_url")
                            if not img_url:
                                versions = node.get("image_versions2", {}).get("candidates", [])
                                if versions:
                                    img_url = versions[0].get("url")

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
    
    @tasks.loop(seconds=600)
    async def instagram_task(self):
        post_data = await self.get_latest_post()
        if post_data:
            print(f"DEBUG: ID API: {post_data['id']} | Memori Bot: {self.last_post_id}")
            
            if self.last_post_id != post_data["id"]:
                self.last_post_id = post_data["id"] 
                
                guild_id = int(self.config["DISCORD"]["GUILD_ID"])
                channel_name = self.config["INSTAGRAM"]["CHANNEL"]
                
                guild = self.bot.get_guild(guild_id)
                if guild:
                    channel = discord.utils.get(guild.channels, name=channel_name)
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
        # Tambahkan Cog secara manual di sini
        await bot.add_cog(Instagram(bot, config))
        await bot.start(config["DISCORD"]["TOKEN"])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot dimatikan.")
