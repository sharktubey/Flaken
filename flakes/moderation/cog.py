import json
from datetime import timedelta
from pathlib import Path

import discord
from discord.ext import commands


BLOCKED_ROLE_ID = 1527813495188357331


class ModerationSuite(commands.Cog):
    """Warn, kick, ban, purge, timeout -- full moderation toolkit."""

    def __init__(
        self,
        bot: commands.Bot,
        warn_data_path: str = "warns.json",
    ):
        self.bot = bot
        self.warn_path = Path(warn_data_path)
        self.warns: dict[str, list[dict]] = {}
        self._load()

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.guild and any(r.id == BLOCKED_ROLE_ID for r in ctx.author.roles):
            await ctx.send("You are not allowed to use moderation commands.", ephemeral=True)
            return False
        return True

    def _load(self):
        if self.warn_path.exists():
            self.warns = json.loads(self.warn_path.read_text())

    def _save(self):
        self.warn_path.write_text(json.dumps(self.warns, indent=2))

    @commands.hybrid_command(name="kick")
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        await member.kick(reason=reason)
        await ctx.send(f"Kicked {member.mention} | Reason: {reason}")

    @commands.hybrid_command(name="ban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        await member.ban(reason=reason)
        await ctx.send(f"Banned {member.mention} | Reason: {reason}")

    @commands.hybrid_command(name="purge")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int):
        deleted = await ctx.channel.purge(limit=min(amount, 100) + 1)
        await ctx.send(f"Deleted {len(deleted) - 1} messages", delete_after=3)

    @commands.hybrid_command(name="warn")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        uid = str(member.id)
        if uid not in self.warns:
            self.warns[uid] = []
        self.warns[uid].append({
            "reason": reason,
            "by": str(ctx.author),
            "at": ctx.message.created_at.isoformat(),
        })
        self._save()
        await ctx.send(f"Warned {member.mention} | Reason: {reason} (Total warns: {len(self.warns[uid])})")

    @commands.hybrid_command(name="warns")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def warns(self, ctx: commands.Context, member: discord.Member):
        uid = str(member.id)
        entries = self.warns.get(uid, [])
        if not entries:
            await ctx.send(f"{member.mention} has no warnings.")
            return
        lines = [f"{i+1}. {e['reason']} (by {e['by']})" for i, e in enumerate(entries)]
        await ctx.send(f"**Warns for {member.display_name}**\n" + "\n".join(lines))

    @commands.hybrid_command(name="timeout")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "No reason"):
        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await ctx.send(f"Timed out {member.mention} for {minutes} min | Reason: {reason}")


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationSuite(bot))
