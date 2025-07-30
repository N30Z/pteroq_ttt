-- Sends player deaths and round end events to the Discord bot
-- Place this file in garrysmod/lua/autorun/server
if SERVER then
    local baseUrl = CreateConVar("discord_bot_url", "http://127.0.0.1:5000", FCVAR_ARCHIVE, "Discord bot webhook base URL")
    local linksFile = "discord_links.txt"
    local links = util.JSONToTable(file.Read(linksFile, "DATA") or "{}") or {}

    local function saveLinks()
        file.Write(linksFile, util.TableToJSON(links))
    end

    local function send(endpoint, payload)
        local url = string.TrimRight(baseUrl:GetString(), "/") .. endpoint
        http.Post(url, payload or {}, function() end, function(err) print("Discord bot HTTP error", err) end)
    end

    hook.Add("PlayerDeath", "DiscordBotPlayerDeath", function(vic)
        if not IsValid(vic) or not vic:IsPlayer() then return end
        local discordId = links[vic:SteamID()] or links[vic:SteamID64()]
        if discordId then
            send("/dead", {discord_id = discordId})
        end
    end)

    hook.Add("TTTEndRound", "DiscordBotRoundEnd", function()
        send("/round_end")
    end)

    hook.Add("PlayerSay", "DiscordBotLink", function(ply, text)
        local id = string.match(string.Trim(text), "^!link%s+(%d+)$")
        if not id then return end
        links[ply:SteamID()] = id
        saveLinks()
        ply:ChatPrint("Discord account linked.")
        return ""
    end)
end
