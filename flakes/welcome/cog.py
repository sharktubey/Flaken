from datetime import datetime

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
            embed = discord.Embed(
                title="Welcome!",
                description=msg,
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{len(guild.members)}")
            await channel.send(embed=embed)
        if self.auto_role_name:
            role = discord.utils.get(guild.roles, name=self.auto_role_name)
            if role:
                await member.add_roles(role)

    @commands.hybrid_command(name="setwelcome")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setwelcome(self, ctx: commands.Context, channel: discord.TextChannel):
        self.welcome_channel_name = channel.name
        embed = discord.Embed(
            title="Welcome Channel Set",
            description=f"Welcome messages will be sent to {channel.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="setwelcomemsg")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setwelcomemsg(self, ctx: commands.Context, *, message: str):
        self.welcome_message = message
        embed = discord.Embed(
            title="Welcome Message Updated",
            description=f"New message:\n```{message}```",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )
        embed.set_footer(text="Use {member} to mention the new user")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeSystem(bot))
