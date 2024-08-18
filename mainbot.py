import asyncio
import logging
from typing import cast

import discord
from discord.ext import commands
from discord import app_commands

import wavelink

from config import BOT_TOKEN


class Bot(commands.Bot):
    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True

        discord.utils.setup_logging(level=logging.INFO)
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        nodes = [wavelink.Node(uri="http://localhost:2333", password="youshallnotpass")]
        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)

    async def on_ready(self) -> None:
        logging.info(f"Logged in: {self.user} | {self.user.id}")

    async def on_wavelink_node_ready(
        self, payload: wavelink.NodeReadyEventPayload
    ) -> None:
        logging.info(
            f"Wavelink Node connected: {payload.node!r} | Resumed: {payload.resumed}"
        )

    async def on_wavelink_track_start(
        self, payload: wavelink.TrackStartEventPayload
    ) -> None:
        player: wavelink.Player | None = payload.player
        if not player:
            return

        track: wavelink.Playable = payload.track

        if player.queue.mode == wavelink.QueueMode.loop:
            return

        embed: discord.Embed = discord.Embed(title="Now Playing")
        embed.description = f"**{track.title}** by `{track.author}`"

        if track.artwork:
            embed.set_image(url=track.artwork)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Skip", style=discord.ButtonStyle.primary, custom_id="skip_button"
            )
        )

        await player.home.send(embed=embed, view=view)


bot: Bot = Bot()


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id")
        if custom_id == "skip_button":
            player: wavelink.Player = cast(
                wavelink.Player, interaction.guild.voice_client
            )
            if player:
                await interaction.response.send_message(
                    f"Skipped **{player.current.title}**.", ephemeral=True
                )
                await player.skip(force=True)
                await interaction.message.delete()


@bot.command()
async def play(ctx: commands.Context, *, query: str) -> None:
    if not ctx.guild:
        return

    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        except AttributeError:
            await ctx.send(
                "Please join a voice channel first before using this command."
            )
            return
        except discord.ClientException:
            await ctx.send("I was unable to join this voice channel. Please try again.")
            return

    player.autoplay = wavelink.AutoPlayMode.enabled

    if not hasattr(player, "home"):
        player.home = ctx.channel
    elif player.home != ctx.channel:
        await ctx.send(
            f"You can only play songs in {player.home.mention}, as the player has already started there."
        )
        return

    tracks: wavelink.Search = await wavelink.Playable.search(query)
    if not tracks:
        await ctx.send(
            f"{ctx.author.mention} - Could not find any tracks with that query. Please try again."
        )
        return

    if isinstance(tracks, wavelink.Playlist):
        added: int = await player.queue.put_wait(tracks)
        await ctx.send(
            f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue."
        )
    else:
        track: wavelink.Playable = tracks[0]
        await player.queue.put_wait(track)
        if player.playing:
            await ctx.send(f"Added **`{track}`** to the queue.")

    if not player.playing:
        await player.play(player.queue.get(), volume=30)


@bot.command()
async def skip(ctx: commands.Context) -> None:
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return

    await ctx.send(f"Skipped {player.current.title}.")
    await player.skip(force=True)
    await ctx.message.add_reaction("\u2705")


async def main() -> None:
    async with bot:
        await bot.start(BOT_TOKEN)


asyncio.run(main())
