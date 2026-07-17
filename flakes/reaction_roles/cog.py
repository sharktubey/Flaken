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

    @commands.hybrid_command(name="setupreaction")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setup_reaction(self, ctx: commands.Context, message_id: str, emoji: str, role: discord.Role):
        """Link an emoji reaction to a role on a message."""
        msg_id = int(message_id)
        if msg_id not in self.mappings:
            self.mappings[msg_id] = {}
        self.mappings[msg_id][emoji] = role.id
        self._save()

        try:
            msg = await ctx.channel.fetch_message(msg_id)
            await msg.add_reaction(emoji)
        except Exception:
            pass

        await ctx.send(f"Reaction role set: {emoji} -> {role.name}")

    @commands.hybrid_command(name="removereaction")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def remove_reaction(self, ctx: commands.Context, message_id: str, emoji: str):
        """Remove a reaction-role mapping."""
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
        if member:
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
        if member:
            await member.remove_roles(role)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRoles(bot))
