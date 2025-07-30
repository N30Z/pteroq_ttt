import os
import asyncio
import logging
import re
from typing import List, Optional

from aiohttp import web
import discord
import requests
from discord.ext import commands

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
PTERO_HOST = os.environ.get('PTERO_HOST')
PTERO_KEY = os.environ.get('PTERO_KEY')
PTERO_SERVER_ID = os.environ.get('PTERO_SERVER_ID')

GUILD_ID = int(os.environ.get('GUILD_ID', '0')) or None
ALIVE_CHANNEL_ID = int(os.environ.get('ALIVE_CHANNEL_ID', '0')) or None
DEAD_CHANNEL_ID = int(os.environ.get('DEAD_CHANNEL_ID', '0')) or None
WEBHOOK_PORT = int(os.environ.get('WEBHOOK_PORT', '5000'))

HEADERS = {
    "Authorization": f"Bearer {PTERO_KEY}",
    "Accept": "Application/vnd.pterodactyl.v1+json",
    "Content-Type": "application/json",
}

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="/", intents=intents)

ADMIN_ROLE = "TTT_Admin"


async def _move_member(member: discord.Member, channel_id: int) -> None:
    channel = member.guild.get_channel(channel_id)
    if channel and member.voice:
        await member.move_to(channel)


async def _move_all(from_id: int, to_id: int, guild: discord.Guild) -> None:
    from_chan = guild.get_channel(from_id)
    to_chan = guild.get_channel(to_id)
    if not from_chan or not to_chan:
        return
    for member in from_chan.members:
        await _move_member(member, to_id)


def _power_action(signal: str) -> str:
    if not all([PTERO_HOST, PTERO_KEY, PTERO_SERVER_ID]):
        return "Pterodactyl API environment not configured."
    url = f"{PTERO_HOST}/api/client/servers/{PTERO_SERVER_ID}/power"
    try:
        resp = requests.post(url, json={"signal": signal}, headers=HEADERS, timeout=10)
        if resp.status_code == 204:
            return f"Server {signal} command sent."
        return f"Failed to {signal} server: {resp.text}"
    except Exception as exc:
        return f"Error contacting panel: {exc}"


def _send_command(cmd: str) -> str:
    if not all([PTERO_HOST, PTERO_KEY, PTERO_SERVER_ID]):
        return "Pterodactyl API environment not configured."
    url = f"{PTERO_HOST}/api/client/servers/{PTERO_SERVER_ID}/command"
    try:
        resp = requests.post(url, json={"command": cmd}, headers=HEADERS, timeout=10)
        if resp.status_code == 204:
            return "Command sent."
        return f"Failed to send command: {resp.text}"
    except Exception as exc:
        return f"Error contacting panel: {exc}"


def _list_maps() -> List[str]:
    if not all([PTERO_HOST, PTERO_KEY, PTERO_SERVER_ID]):
        return []
    url = f"{PTERO_HOST}/api/client/servers/{PTERO_SERVER_ID}/files/list?directory=/garrysmod/maps"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        files = resp.json().get("data", [])
        return [f["name"].rsplit(".", 1)[0] for f in files if f["name"].endswith(".bsp")]
    except Exception:
        return []


def _change_map(mapname: str) -> str:
    return _send_command(f"changelevel {mapname}")


def _collection_items(collection_id: str) -> Optional[List[str]]:
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetCollectionDetails/v1/"
    try:
        resp = requests.post(
            url,
            data={"collectioncount": 1, "publishedfileids[0]": collection_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        children = data["response"]["collectiondetails"][0].get("children", [])
        return [c["publishedfileid"] for c in children]
    except Exception:
        return None


def is_admin():
    async def predicate(ctx: commands.Context):
        role_names = [r.name for r in ctx.author.roles]
        return ADMIN_ROLE in role_names
    return commands.check(predicate)


@bot.command(name="start")
@is_admin()
async def start_server(ctx: commands.Context):
    """Starts the server"""
    msg = await asyncio.to_thread(_power_action, "start")
    await ctx.reply(msg)


@bot.command(name="stop")
@is_admin()
async def stop_server(ctx: commands.Context):
    """Stops the server"""
    msg = await asyncio.to_thread(_power_action, "stop")
    await ctx.reply(msg)


@bot.command(name="add")
@is_admin()
async def add_mod(ctx: commands.Context, link: str):
    """Adds a workshop mod link or collection"""
    if not link.startswith("http"):
        await ctx.reply("Please provide a valid workshop link.")
        return

    id_match = re.search(r"id=(\d+)", link)
    if not id_match:
        await ctx.reply("Could not find workshop id in link.")
        return
    workshop_id = id_match.group(1)
    mods_file = "mods.txt"

    if "collection" in link:
        items = await asyncio.to_thread(_collection_items, workshop_id)
        if not items:
            await ctx.reply("Failed to fetch collection details.")
            return
        try:
            with open(mods_file, "a", encoding="utf-8") as f:
                for item in items:
                    f.write(
                        f"https://steamcommunity.com/sharedfiles/filedetails/?id={item}\n"
                    )
            await ctx.reply(f"Added {len(items)} items from collection.")
        except Exception as exc:
            await ctx.reply(f"Failed to add mods: {exc}")
    else:
        try:
            with open(mods_file, "a", encoding="utf-8") as f:
                f.write(link + "\n")
            await ctx.reply("Mod link added.")
        except Exception as exc:
            await ctx.reply(f"Failed to add mod: {exc}")


@bot.command(name="link")
async def link_account(ctx: commands.Context):
    """DMs the user with linking instructions"""
    try:
        await ctx.author.send(
            "Use the in-game chat command '!link {discord_id}' to link your account.".format(
                discord_id=ctx.author.id
            )
        )
        await ctx.reply("Check your DMs for linking instructions.")
    except discord.Forbidden:
        await ctx.reply("I can't DM you. Please check your privacy settings.")


@bot.command(name="setalive")
@is_admin()
async def set_alive(ctx: commands.Context, channel: discord.VoiceChannel):
    """Sets the voice channel for alive players"""
    global ALIVE_CHANNEL_ID
    ALIVE_CHANNEL_ID = channel.id
    await ctx.reply(f"Alive channel set to {channel.name}")


@bot.command(name="setdead")
@is_admin()
async def set_dead(ctx: commands.Context, channel: discord.VoiceChannel):
    """Sets the voice channel for dead players"""
    global DEAD_CHANNEL_ID
    DEAD_CHANNEL_ID = channel.id
    await ctx.reply(f"Dead channel set to {channel.name}")


@bot.command(name="map")
@is_admin()
async def map_command(ctx: commands.Context, arg: str):
    """Lists maps or changes the current map"""
    if arg == "list":
        maps = await asyncio.to_thread(_list_maps)
        if not maps:
            await ctx.reply("No maps found.")
        else:
            await ctx.reply(", ".join(maps))
    else:
        msg = await asyncio.to_thread(_change_map, arg)
        await ctx.reply(msg)


@bot.command(name="roundover")
@is_admin()
async def round_over(ctx: commands.Context):
    """Moves all players back to the alive channel"""
    if not ALIVE_CHANNEL_ID or not DEAD_CHANNEL_ID:
        await ctx.reply("Channels not configured")
        return
    await _move_all(DEAD_CHANNEL_ID, ALIVE_CHANNEL_ID, ctx.guild)
    await ctx.reply("Round ended. Players moved back.")


async def _handle_dead(request: web.Request) -> web.Response:
    if not DEAD_CHANNEL_ID:
        return web.json_response({"error": "dead channel not set"}, status=400)
    data = await request.json()
    discord_id = data.get("discord_id")
    guild = bot.get_guild(GUILD_ID)
    if not guild or not discord_id:
        return web.json_response({"error": "bad request"}, status=400)
    member = guild.get_member(int(discord_id))
    if not member:
        return web.json_response({"error": "member not found"}, status=404)
    await _move_member(member, DEAD_CHANNEL_ID)
    return web.json_response({"status": "moved"})


async def _handle_round_end(request: web.Request) -> web.Response:
    if not ALIVE_CHANNEL_ID or not DEAD_CHANNEL_ID:
        return web.json_response({"error": "channels not set"}, status=400)
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return web.json_response({"error": "guild not found"}, status=404)
    await _move_all(DEAD_CHANNEL_ID, ALIVE_CHANNEL_ID, guild)
    return web.json_response({"status": "ok"})


async def _run_webhook() -> None:
    app = web.Application()
    app.router.add_post('/dead', _handle_dead)
    app.router.add_post('/round_end', _handle_round_end)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN environment variable not set")
    await _run_webhook()
    await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
