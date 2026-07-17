import discord
from discord.ext import commands


class TicketSystem(commands.Cog):
    """Ticket system -- users create tickets with a button, staff claim and close."""

    def __init__(
        self,
        bot: commands.Bot,
        category_name: str = "tickets",
        staff_role_name: str = "Staff",
    ):
        self.bot = bot
        self.category_name = category_name
        self.staff_role_name = staff_role_name

    async def _get_or_create_category(self, guild: discord.Guild) -> discord.CategoryChannel:
        category = discord.utils.get(guild.categories, name=self.category_name)
        if not category:
            category = await guild.create_category(self.category_name)
        return category

    @commands.hybrid_command(name="ticketpanel")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx: commands.Context):
        """Send the ticket creation panel in the current channel."""
        embed = discord.Embed(
            title="Create a Ticket",
            description="Click the button below to open a support ticket.",
            color=discord.Color.blue(),
        )
        view = TicketView(self)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="close")
    @commands.guild_only()
    async def close(self, ctx: commands.Context):
        """Close the current ticket channel."""
        staff_role = discord.utils.get(ctx.guild.roles, name=self.staff_role_name)
        if staff_role and staff_role not in ctx.author.roles:
            if ctx.author != ctx.guild.owner:
                await ctx.send("Only staff can close tickets.")
                return
        await ctx.send("Ticket closed. Deleting channel in 5 seconds...", delete_after=4)
        await ctx.channel.delete(reason="Ticket closed")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        if interaction.data.get("custom_id") != "create_ticket":
            return
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        category = await self._get_or_create_category(guild)
        staff_role = discord.utils.get(guild.roles, name=self.staff_role_name)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        name = f"ticket-{interaction.user.name.lower()}"
        channel = await guild.create_text_channel(name, category=category, overwrites=overwrites)

        embed = discord.Embed(
            title="Ticket Created",
            description=f"Ticket created by {interaction.user.mention}. Staff will be with you shortly.\n\nUse `/close` when done.",
            color=discord.Color.green(),
        )
        await channel.send(content=staff_role.mention if staff_role else "", embed=embed)
        await interaction.followup.send(f"Ticket created: {channel.mention}", ephemeral=True)


class TicketView(discord.ui.View):
    def __init__(self, cog: TicketSystem):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket", emoji="🎫")
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.on_interaction(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketSystem(bot))
