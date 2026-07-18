from datetime import datetime

import discord
from discord.ext import commands


class HelpCommand(commands.Cog):
    """Interactive help with embed pages and navigation buttons."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Show all available commands")
    @commands.guild_only()
    async def help(self, ctx: commands.Context):
        """Show all available commands grouped by flake."""
        pages = self._build_pages(ctx)
        view = HelpView(pages, ctx.author)
        await ctx.send(embed=pages[0], view=view)

    def _build_pages(self, ctx: commands.Context) -> list[discord.Embed]:
        pages = []
        intro = discord.Embed(
            title="Flaken Bot",
            description="A modular Discord bot built with the Flaken library.\n\nSelect a category below to view commands.",
            color=discord.Color.purple(),
            timestamp=datetime.now(),
        )
        intro.set_footer(text="Flaken Bot | Use the buttons to navigate")
        cog_names = [n for n in self.bot.cogs if n != "HelpCommand"]
        for name in cog_names:
            cog = self.bot.cogs[name]
            cmds = cog.get_commands()
            if cmds:
                intro.add_field(name=name, value=f"{len(cmds)} commands", inline=True)
        pages.append(intro)

        for name in cog_names:
            cog = self.bot.cogs[name]
            cmds = cog.get_commands()
            if not cmds:
                continue
            embed = discord.Embed(
                title=name,
                description=cog.description or "",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )
            embed.set_footer(text="Flaken Bot")
            for cmd in cmds:
                sig = cmd.signature or ""
                prefix_cmd = f"`{ctx.prefix}{cmd.name} {sig}`" if sig else f"`{ctx.prefix}{cmd.name}`"
                slash_cmd = f"`/{cmd.name}`"
                desc = cmd.description or cmd.help or "No description"
                embed.add_field(name=f"{prefix_cmd} / {slash_cmd}", value=desc, inline=False)
            pages.append(embed)
        return pages


class HelpView(discord.ui.View):
    def __init__(self, pages: list[discord.Embed], author: discord.Member):
        super().__init__(timeout=None)
        self.pages = pages
        self.author = author
        self.current = 0
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.current == 0
        self.prev_btn.label = "<< Home" if self.current == 1 else "< Prev"
        self.next_btn.disabled = self.current == len(self.pages) - 1
        self.page_counter.label = f"{self.current + 1} / {len(self.pages)}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("Not your help menu.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="< Prev", style=discord.ButtonStyle.gray)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="1 / 1", style=discord.ButtonStyle.gray, disabled=True)
    async def page_counter(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="Next >", style=discord.ButtonStyle.gray)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCommand(bot))
