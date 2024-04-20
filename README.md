# Z4 Music

This Discord bot allows users to play music in voice channels using the Wavelink library.

### Note: Use the Lavalink version provided otherwise the bot may not work.

## Installation

1. Clone this repository:

    ```bash
    git clone https://github.com/AnasGrzor/Z4-Music-Discord-Music-Bot.git
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Obtain a bot token from the [Discord Developer Portal](https://discord.com/developers/applications).

4. Configure the bot token and other settings in the code.

5. Run the bot:

    ```bash
    python bot.py
    ```

## Usage

- Use `!play <query>` to play a song with the given query.
- Use `!skip` to skip the current song.
- Use `!seek <seconds>` to seek to a specific position in the currently playing track.
- Use `!nightcore` to set the filter to a nightcore style.
- Use `!slowed` to set the filter to a slowed style.
- Use `rmfilter` to remove all filters.
- Use `!toggle`, `!pause`, or `!resume` to pause or resume the player.
- Use `!volume <value>` to change the volume of the player.
- Use `!queue` to display the current queue.
- Use `!shuffle` to shuffle the queue.
- Use `!remove <song_name>` to remove a song from the queue by name.
- Use `!clear` to clear the queue.
- Use `!loop` to toggle looping the current song.
- Use `!disconnect` or `!dc` to disconnect the player.

## Configuration

- Set the bot token in the `main()` function.
- Configure other settings in the code as needed.

## Contributing

Contributions are welcome! Feel free to submit bug reports or pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
