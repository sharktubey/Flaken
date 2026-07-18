import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands


class LevelingSystem(commands.Cog):
    """XP & leveling -- tracks messages, awards XP, and shows leaderboards."""

    def __init__(
        self,
        bot: commands.Bot,
        xp_per_message: int = 15,
        xp_cooldown: int = 60,
        levels: dict[str, int] | None = None,
        data_path: str = "leveling_data.json",
    ):
        self.bot = bot
        self.xp_per_message = xp_per_message
        self.xp_cooldown = xp_cooldown
        self.levels = levels or {"1": 0, "5": 100, "10": 500, "15": 1500, "20": 5000}
        self.data_path = Path(data_path)
        self.data: dict[str, dict] = {}
        self._cooldowns: dict[int, float] = {}
        self._load()

    def _load(self):
        if self.data_path.exists():
            self.data = json.loads(self.data_path.read_text())

    def _save(self):
        self.data_path.write_text(json.dumps(self.data, indent=2))

    def _get_level(self, xp: int) -> int:
        level = 1
        for lvl, req in sorted(self.levels.items(), key=lambda x: int(x[0])):
            if xp >= req:
                level = int(lvl)
        return level

    def _xp_for_next_level(self, xp: int) -> int:
        next_lvl = self._get_level(xp) + 1
        return self.levels.get(str(next_lvl), xp + 100) - xp

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.content.startswith(tuple(self.bot.command_prefix)):
            return
        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        key = f"{guild_id}:{user_id}"
        now = message.created_at.timestamp()
        last = self._cooldowns.get(message.author.id, 0)
        if now - last < self.xp_cooldown:
            return
        self._cooldowns[message.author.id] = now
        entry = self.data.get(key, {"xp": 0, "level": 1})
        old_level = entry["level"]
        entry["xp"] += self.xp_per_message + random.randint(-5, 5)
        entry["level"] = self._get_level(entry["xp"])
        self.data[key] = entry
        self._save()
        if entry["level"] > old_level:
            embed = discord.Embed(
                title="Level Up!",
                description=f"{message.author.mention} reached **level {entry['level']}**!",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            embed.set_footer(text="Keep chatting to earn more XP")
            await message.channel.send(embed=embed)

    @commands.hybrid_command(name="rank", description="View your rank and XP for this server")
    @commands.guild_only()
    async def rank(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target = member or ctx.author
        key = f"{ctx.guild.id}:{target.id}"
        entry = self.data.get(key, {"xp": 0, "level": 1})
        xp_needed = self._xp_for_next_level(entry["xp"])
        next_lvl = entry["level"] + 1

        embed = discord.Embed(
            title=f"{target.display_name}'s Rank",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Level", value=str(entry["level"]), inline=True)
        embed.add_field(name="Total XP", value=str(entry["xp"]), inline=True)
        embed.add_field(name="Next Level", value=f"{xp_needed} XP to level {next_lvl}", inline=False)
        embed.set_footer(text="Flaken Leveling System")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="leaderboard", description="Show the server XP leaderboard top 10")
    @commands.guild_only()
    async def leaderboard(self, ctx: commands.Context):
        guild_data = {
            k: v for k, v in self.data.items() if k.startswith(f"{ctx.guild.id}:")
        }
        sorted_users = sorted(guild_data.items(), key=lambda x: x[1]["xp"], reverse=True)[:10]
        if not sorted_users:
            await ctx.send("No data yet -- start chatting to earn XP!")
            return
        lines = []
        medals = [":first_place:", ":second_place:", ":third_place:"] + [""] * 7
        for i, (key, entry) in enumerate(sorted_users, 1):
            user_id = key.split(":")[1]
            user = ctx.guild.get_member(int(user_id))
            name = user.display_name if user else f"Unknown ({user_id})"
            medal = medals[i - 1] if i <= 3 else f"`{i:2d}.`"
            lines.append(f"{medal} **{name}** -- Level {entry['level']} ({entry['xp']} XP)")
        embed = discord.Embed(
            title="Server Leaderboard",
            description="\n".join(lines),
            color=discord.Color.gold(),
            timestamp=datetime.now(),
        )
        embed.set_footer(text="Top 10 by XP")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LevelingSystem(bot))
