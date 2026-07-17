import discord
from discord.ext import commands


class HelpCommand(commands.Cog):
    """Interactive help with embed pages and navigation buttons."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="help")
    @commands.guild_only()
    async def help(self, ctx: commands.Context):
        """Show all available commands grouped by flake."""
        pages = self._build_pages(ctx)
        view = HelpView(pages, ctx.author)
        await ctx.send(embed=pages[0], view=view)

    def _build_pages(self, ctx: commands.Context) -> list[discord.Embed]:
        pages = []
        # Intro page
        intro = discord.Embed(
            title="Flaken Bot Commands",
            description="Select a category below to see available commands.",
            color=discord.Color.purple(),
        )
        cog_names = [name for name in self.bot.cogs if name != "HelpCommand"]
        for name in cog_names:
            cog = self.bot.cogs[name]
            cmds = cog.get_commands()
            if cmds:
                intro.add_field(name=name, value=f"{len(cmds)} commands", inline=True)
        pages.append(intro)

        # Per-cog pages
        for name in cog_names:
            cog = self.bot.cogs[name]
            cmds = cog.get_commands()
            if not cmds:
                continue
            embed = discord.Embed(
                title=name,
                description=cog.description or "",
                color=discord.Color.blue(),
            )
            for cmd in cmds:
                sig = f"{ctx.prefix}{cmd.name} {cmd.signature}" if cmd.signature else f"{ctx.prefix}{cmd.name}"
                embed.add_field(name=f"/{cmd.name}", value=f"`{sig}`\n{cmd.description or cmd.help or ''}", inline=False)
            pages.append(embed)

        return pages


class HelpView(discord.ui.View):
    def __init__(self, pages: list[discord.Embed], author: discord.Member):
        super().__init__(timeout=60)
        self.pages = pages
        self.author = author
        self.current = 0
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.current == 0
        self.next_btn.disabled = self.current == len(self.pages) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("Not your help menu.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="<", style=discord.ButtonStyle.gray)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label=">", style=discord.ButtonStyle.gray)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCommand(bot))
