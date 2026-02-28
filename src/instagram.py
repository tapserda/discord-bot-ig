import discord
from discord.ext import commands, tasks
import aiohttp
import os

class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Ambil semua data dari Variables Railway
        self.api_key = os.environ.get("RAPIDAPI_KEY")
        self.username = os.environ.get("IG_USERNAME")
        self.guild_id = int(os.environ.get("DISCORD_GUILD_ID"))
        self.channel_name = os.environ.get("DISCORD_CHANNEL_NAME")
        
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
                        # Navigasi struktur JSON sesuai image_639058.png
                        result = data.get("result", {})
                        edges = result.get("edges", [])
                        
                        if edges:
                            node = edges[0].get("node", {})
                            caption_text = node.get("caption", {}).get("text", "No Caption")
                            return {
                                "id": node.get("id"),
                                "shortcode": node.get("code"),
                                "image": node.get("display_url"),
                                "caption": caption_text
                            }
            except Exception as e:
                print(f"Error fetching IG: {e}")
        return None

    @tasks.loop(hours=4) # Pengecekan tiap 4 jam sekali
    async def instagram_task(self):
        print(f"--- Checking @{self.username} (4h interval) ---")
        post_data = await self.get_latest_post()
        
        if post_data and self.last_post_id != post_data["id"]:
            self.last_post_id = post_data["id"]
            
            guild = self.bot.get_guild(self.guild_id)
            if guild:
                channel = discord.utils.get(guild.channels, name=self.channel_name)
                if channel:
                    link = f"https://www.instagram.com/p/{post_data['shortcode']}/"
                    embed = discord.Embed(
                        title=f"📸 New Drop from @{self.username}",
                        description=post_data["caption"][:300] + "...",
                        url=link,
                        color=0xbc2a8d
                    )
                    if post_data["image"]:
                        embed.set_image(url=post_data["image"])
                    embed.set_footer(text="Instagram Forwarder by SAIKO SOCIETY") #
                    
                    await channel.send(embed=embed)
                    print(f"--- [SUCCESS] Sent to Discord: {post_data['shortcode']} ---")

    @instagram_task.before_loop
    async def before_instagram_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):

    await bot.add_cog(Instagram(bot))
