# Trouble in Terrorist Town Pterodactyl Egg

This repository contains a Pterodactyl egg for running a Garry's Mod server with the **Trouble in Terrorist Town** (TTT) game mode.

## Usage
1. Import `ttt_egg.json` into your Pterodactyl panel.
2. When creating a server, fill in the Steam credentials and the game login token.
3. The included installation script installs the server via SteamCMD.

## Discord Bot
`bot.py` provides a simple Discord bot for controlling the server and moving
players between voice channels.
Set the following environment variables before running it:

- `BOT_TOKEN` – your Discord bot token
- `PTERO_HOST` – URL to your Pterodactyl panel
- `PTERO_KEY` – API key for the panel
- `PTERO_SERVER_ID` – the server ID to control
- `GUILD_ID` – Discord guild ID the bot operates in
- `ALIVE_CHANNEL_ID` – voice channel for alive players (optional)
- `DEAD_CHANNEL_ID` – voice channel for dead players (optional)
- `WEBHOOK_PORT` – port for the in-game webhook (default 5000)

Commands tagged with **Admin** require the Discord role `TTT_Admin`.

Available commands:
- `/start` – start the server **Admin**
- `/stop` – stop the server **Admin**
- `/add <link>` – add a workshop link or collection **Admin**
- `/link` – DM the user with linking instructions
- `/setalive <channel>` – set the alive voice channel **Admin**
- `/setdead <channel>` – set the dead voice channel **Admin**
- `/map list` – list installed maps **Admin**
- `/map <name>` – change to the given map **Admin**
- `/roundover` – manually move dead players back **Admin**

The bot exposes HTTP endpoints on `/dead` and `/round_end` that can be called
from a game server plugin to move a single player or automatically reset all
players at the end of a round.

## Game Server Mod
The `lua/autorun/server/discord_bot.lua` script sends player deaths and round
end events to the Discord bot. Copy it into your server's
`garrysmod/lua/autorun/server/` directory and make sure the ConVar
`discord_bot_url` points to the bot's webhook (e.g. `http://localhost:5000`).
Players can link their Discord account in-game with `!link <discord_id>`.
