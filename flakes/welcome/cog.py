import discord
from discord.ext import commands


class WelcomeSystem(commands.Cog):
    """Greet new members and assign roles automatically."""

    def __init__(
        self,
        bot: commands.Bot,
        welcome_channel_name: str = "welcome",
        welcome_message: str = "Welcome to the server, {member}!",
        auto_role_name: str = "",
    ):
        self.bot = bot
        self.welcome_channel_name = welcome_channel_name
        self.welcome_message = welcome_message
        self.auto_role_name = auto_role_name

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        channel = discord.utils.get(guild.text_channels, name=self.welcome_channel_name)
        if channel:
            msg = self.welcome_message.replace("{member}", member.mention)
            await channel.send(msg)
        if self.auto_role_name:
            role = discord.utils.get(guild.roles, name=self.auto_role_name)
            if role:
                await member.add_roles(role)

    @commands.hybrid_command(name="setwelcome")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setwelcome(self, ctx: commands.Context, channel: discord.TextChannel):
        self.welcome_channel_name = channel.name
        await ctx.send(f"Welcome channel set to {channel.mention}")

    @commands.hybrid_command(name="setwelcomemsg")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setwelcomemsg(self, ctx: commands.Context, *, message: str):
        self.welcome_message = message
        await ctx.send("Welcome message updated!")


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeSystem(bot))
