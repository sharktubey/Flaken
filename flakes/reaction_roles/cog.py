import json
from pathlib import Path

import discord
from discord.ext import commands


class ReactionRoles(commands.Cog):
    """Reaction roles -- users react to a message to self-assign roles."""

    def __init__(self, bot: commands.Bot, data_path: str = "reaction_roles.json"):
        self.bot = bot
        self.data_path = Path(data_path)
        self.mappings: dict[int, dict[str, int]] = {}
        self._load()

    def _load(self):
        if self.data_path.exists():
            raw = json.loads(self.data_path.read_text())
            self.mappings = {int(k): v for k, v in raw.items()}

    def _save(self):
        self.data_path.write_text(json.dumps(self.mappings, indent=2))

    @commands.hybrid_command(name="reactionpanel")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def reaction_panel(self, ctx: commands.Context, title: str, channel: discord.TextChannel | None = None):
        """Create a reaction role panel. Usage: !reactionpanel "Pick a role" #channel"""
        target = channel or ctx.channel
        embed = discord.Embed(
            title=title,
            description="React below to get your roles.\n\n",
            color=discord.Color.purple(),
        )
        msg = await target.send(embed=embed)
        self.mappings[msg.id] = {}
        self._save()
        await ctx.send(f"Reaction panel created in {target.mention}. Use `{ctx.prefix}addreaction {msg.id} :emoji: @role` to add options.")

    @commands.hybrid_command(name="addreaction")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def add_reaction(self, ctx: commands.Context, message_id: str, emoji: str, role: discord.Role):
        """Add a reaction-role to an existing panel message."""
        msg_id = int(message_id)
        if msg_id not in self.mappings:
            await ctx.send("No reaction panel found with that message ID. Create one with `!reactionpanel` first.")
            return
        self.mappings[msg_id][emoji] = role.id
        self._save()

        try:
            msg = await ctx.channel.fetch_message(msg_id)
            await msg.add_reaction(emoji)
        except Exception:
            pass

        embed = discord.Embed(
            title="Reaction Roles",
            description=f"{emoji} -> {role.mention}",
            color=discord.Color.purple(),
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="removereaction")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def remove_reaction(self, ctx: commands.Context, message_id: str, emoji: str):
        """Remove a reaction-role from a panel."""
        msg_id = int(message_id)
        if msg_id in self.mappings and emoji in self.mappings[msg_id]:
            del self.mappings[msg_id][emoji]
            if not self.mappings[msg_id]:
                del self.mappings[msg_id]
            self._save()
            await ctx.send(f"Removed reaction role for {emoji}")
        else:
            await ctx.send("Mapping not found.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if payload.message_id not in self.mappings:
            return
        emoji = str(payload.emoji)
        if emoji not in self.mappings[payload.message_id]:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        role = guild.get_role(self.mappings[payload.message_id][emoji])
        if not role:
            return
        member = guild.get_member(payload.user_id)
        if member and role not in member.roles:
            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if payload.message_id not in self.mappings:
            return
        emoji = str(payload.emoji)
        if emoji not in self.mappings[payload.message_id]:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        role = guild.get_role(self.mappings[payload.message_id][emoji])
        if not role:
            return
        member = guild.get_member(payload.user_id)
        if member and role in member.roles:
            await member.remove_roles(role)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRoles(bot))
