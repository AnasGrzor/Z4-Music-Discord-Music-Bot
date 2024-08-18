

import asyncio
import logging
from typing import cast

import discord
from discord.ext import commands

import wavelink



class Bot(commands.Bot):
    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True

        discord.utils.setup_logging(level=logging.INFO)
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        nodes = [wavelink.Node(uri="http://localhost:2333", password="youshallnotpass")]

        # cache_capacity is EXPERIMENTAL. Turn it off by passing None
        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)

    async def on_ready(self) -> None:
        logging.info(f"Logged in: {self.user} | {self.user.id}")

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        logging.info(f"Wavelink Node connected: {payload.node!r} | Resumed: {payload.resumed}")

    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: wavelink.Player | None = payload.player
        if not player:
            # Handle edge cases...
            return

        original: wavelink.Playable | None = payload.original
        track: wavelink.Playable = payload.track

        # Check if the queue mode is set to loop
        if player.queue.mode == wavelink.QueueMode.loop:
            return  # Don't send the "Now Playing" message if the queue is set to loop

        embed: discord.Embed = discord.Embed(title="Now Playing")
        embed.description = f"**{track.title}** by `{track.author}`"

        if track.artwork:
            embed.set_image(url=track.artwork)

        if original and original.recommended:
            embed.description += f"\n\n`This track was recommended via {track.source}`"

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)    

        await player.home.send(embed=embed)


bot: Bot = Bot()


@bot.command()
async def play(ctx: commands.Context, *, query: str) -> None:
    """Play a song with the given query."""
    if not ctx.guild:
        return

    player: wavelink.Player
    player = cast(wavelink.Player, ctx.voice_client)  # type: ignore

    if not player:
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)  # type: ignore
        except AttributeError:
            await ctx.send("Please join a voice channel first before using this command.")
            return
        except discord.ClientException:
            await ctx.send("I was unable to join this voice channel. Please try again.")
            return

    # Turn on AutoPlay to enabled mode.
    # enabled = AutoPlay will play songs for us and fetch recommendations...
    # partial = AutoPlay will play songs for us, but WILL NOT fetch recommendations...
    # disabled = AutoPlay will do nothing...
    player.autoplay = wavelink.AutoPlayMode.enabled

    # Lock the player to this channel...
    if not hasattr(player, "home"):
        player.home = ctx.channel
    elif player.home != ctx.channel:
        await ctx.send(f"You can only play songs in {player.home.mention}, as the player has already started there.")
        return

    # This will handle fetching Tracks and Playlists...
    # Seed the doc strings for more information on this method...
    # If spotify is enabled via LavaSrc, this will automatically fetch Spotify tracks if you pass a URL...
    # Defaults to YouTube for non URL based queries...
    tracks: wavelink.Search = await wavelink.Playable.search(query)
    if not tracks:
        await ctx.send(f"{ctx.author.mention} - Could not find any tracks with that query. Please try again.")
        return

    if isinstance(tracks, wavelink.Playlist):
        # tracks is a playlist...
        added: int = await player.queue.put_wait(tracks)
        await ctx.send(f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.")
    else:
        track: wavelink.Playable = tracks[0]
        await player.queue.put_wait(track)
        if player.playing:
            await ctx.send(f"Added **`{track}`** to the queue.")

    if not player.playing:
        # Play now since we aren't playing anything...
        await player.play(player.queue.get(), volume=30)

    # Optionally delete the invokers message...
    # try:
    #     await ctx.message.delete()
    # except discord.HTTPException:
    #     pass

@bot.command()
async def play_lofi(ctx: commands.Context) -> None:
        """Play lo-fi music 24/7."""
        if not ctx.guild:
            return

        player: wavelink.Player
        player = cast(wavelink.Player, ctx.voice_client)  # type: ignore

        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)  # type: ignore
            except AttributeError:
                await ctx.send("Please join a voice channel first before using this command.")
                return
            except discord.ClientException:
                await ctx.send("I was unable to join this voice channel. Please try again.")
                return

        player.autoplay = wavelink.AutoPlayMode.enabled

        if not hasattr(player, "home"):
            player.home = ctx.channel
        elif player.home != ctx.channel:
            await ctx.send(f"You can only play songs in {player.home.mention}, as the player has already started there.")
            return

        lofi_url = "https://www.youtube.com/watch?v=jfKfPfyJRdk"  # Example lo-fi live stream URL
        tracks: wavelink.Search = await wavelink.Playable.search(lofi_url)
        if not tracks:
            await ctx.send(f"{ctx.author.mention} - Could not find any tracks with that query. Please try again.")
            return

        track: wavelink.Playable = tracks[0]
        await player.queue.put_wait(track)

        if not player.playing:
            await player.play(player.queue.get(), volume=30)

@bot.command()
async def skip(ctx: commands.Context) -> None:
    """Skip the current song."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return

    await ctx.send(f"Skipped {player.current.title}.")
    await player.skip(force=True)
    await ctx.message.add_reaction("\u2705")


@bot.command()
async def nightcore(ctx: commands.Context) -> None:
    """Set the filter to a nightcore style."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return

    filters: wavelink.Filters = player.filters
    filters.timescale.set(pitch=1.2, speed=1.2, rate=1)
    await player.set_filters(filters)

    await ctx.message.add_reaction("\u2705")


@bot.command(name="toggle", aliases=["pause", "resume"])
async def pause_resume(ctx: commands.Context) -> None:
    """Pause or Resume the Player depending on its current state."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return

    await player.pause(not player.paused)
    await ctx.message.add_reaction("\u2705")


@bot.command()
async def volume(ctx: commands.Context, value: int) -> None:
    """Change the volume of the player."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        await ctx.send("I'm not connected to a voice channel.")
        return

    await player.set_volume(value)
    await ctx.send(f"Set the volume to {value}%.")
    await ctx.message.add_reaction("\u2705")

@bot.command()
async def queue(ctx: commands.Context) -> None:
    """Display the current queue."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    queue_str: str = "\n".join(f"**{track.title}** by `{track.author}`" for track in player.queue)
    await ctx.send(f"Songs in Queue: {len(player.queue)}")

    if len(player.queue) > 0:
        chunks = [queue_str[i:i+1000] for i in range(0, len(queue_str), 1000)]
        for chunk in chunks:
            await ctx.send(f"Current Queue:\n{chunk}")
    else:
        return

@bot.command()
async def shuffle(ctx: commands.Context) -> None:
    """Shuffle the queue."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    player.queue.shuffle()
    await ctx.send("Shuffled the queue.")

@bot.command()
async def remove(ctx: commands.Context, *, song_name: str) -> None:
    """Remove a song from the queue by name."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    removed_count = 0
    for track in player.queue[:]:  # Iterate over a copy of the queue to avoid modifying it during iteration
        if track.title.lower() == song_name.lower():
            player.queue.remove(track)
            removed_count += 1
    if removed_count > 0:
        await ctx.send(f"Removed {removed_count} instance(s) of **{song_name}** from the queue.")
    else:
        await ctx.send(f"Song **{song_name}** not found in the queue.")


@bot.command()
async def clear(ctx: commands.Context) -> None:
    """Clear the queue."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    player.queue.clear()
    await ctx.send("Cleared the queue.")

@bot.command()
async def loop(ctx: commands.Context) -> None:
    """Toggle looping the current song."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    # Toggle between normal mode and loop mode
    if player.queue.mode == wavelink.QueueMode.normal:
        player.queue.mode = wavelink.QueueMode.loop
        await ctx.send(f"Looped **{player.current.title}**.")
    else:
        player.queue.mode = wavelink.QueueMode.normal
        await ctx.send(f"Unlooped **{player.current.title}**.")


@bot.command(aliases=["dc"])
async def disconnect(ctx: commands.Context) -> None:
    """Disconnect the Player."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return

    await player.disconnect()
    await ctx.message.add_reaction("\u2705")

@bot.command()
async def rmfilter(ctx: commands.Context) -> None:
    """Remove the filters."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    filters: wavelink.Filters = player.filters
    filters.reset()
    await player.set_filters(filters)
    await ctx.message.add_reaction("\u2705")

@bot.command()
async def slowed(ctx: commands.Context) -> None:
    """Set the filter to a slowed style."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return

    filters: wavelink.Filters = player.filters
    filters.timescale.set(pitch=0.9, speed=0.8, rate=1)
    await player.set_filters(filters)

    await ctx.message.add_reaction("\u2705")

@bot.command()
async def seek(ctx: commands.Context, seconds: int = 0) -> None:
    """Seek to the provided position in the currently playing track, in seconds."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    await player.seek(seconds * 1000)  # Convert seconds to milliseconds
    await ctx.message.add_reaction("\u2705")


async def main() -> None:
    async with bot:
        await bot.start("YOUR_TOKEN_HERE")


asyncio.run(main())
