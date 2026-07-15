import json
import random
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands


class LevelingSystem(commands.Cog):
    """XP & leveling — tracks messages, awards XP, assigns roles, and shows leaderboards."""

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
            await message.channel.send(
                f"Level up! {message.author.mention} reached level {entry['level']}!"
            )

    @commands.hybrid_command(name="rank")
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def rank(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target = member or ctx.author
        key = f"{ctx.guild.id}:{target.id}"
        entry = self.data.get(key, {"xp": 0, "level": 1})
        embed = discord.Embed(
            title=f"{target.display_name}'s Rank",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Level", value=str(entry["level"]))
        embed.add_field(name="XP", value=str(entry["xp"]))
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.channel.send(embed=embed)

    @commands.hybrid_command(name="leaderboard")
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
        for i, (key, entry) in enumerate(sorted_users, 1):
            user_id = key.split(":")[1]
            user = ctx.guild.get_member(int(user_id))
            name = user.display_name if user else f"Unknown ({user_id})"
            lines.append(f"**{i}.** {name} -- Level {entry['level']} ({entry['xp']} XP)")
        embed = discord.Embed(
            title="Leaderboard",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LevelingSystem(bot))
