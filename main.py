import asyncio
import os
import json
import re
import random
import aiohttp
import requests
from discord.ext import tasks
import discord
from discord import File
from TikTokApi import TikTokApi
from math import floor
from bs4 import BeautifulSoup
import traceback
from discord.utils import get
from discord.ui import View, Select
from discord.ext import commands
from discord import Button, ButtonStyle, Interaction
from discord import VoiceChannel, Embed, PermissionOverwrite
from datetime import datetime, timezone, timedelta
log_channel_id = 1302716998983221298
rankup_channel_id = 1302369087095046184
ECONOMY_FILE = "economie.json"
NOEL_FILE = "noel.json"
TOTO = ''
debug = True
SERVER = True
intents = discord.Intents().all()
intents.voice_states = True
intents.guilds = True
class PersistentViewBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or('CAS'), help_command=None, case_insensitive=True, intents=intents)

    async def setup_hook(self) -> None:
        views = [RemoteButtonView(), CategorySelectView()]
        for element in views:
            self.add_view(element)
        
bot = PersistentViewBot()

@bot.command()
async def sync(ctx):
    synced = await ctx.bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} commands")

tree = bot.tree

def run_bot(token=TOTO, debug=False):
    if debug: print(bot._connection.loop)
    bot.run(token)
    if debug: print(bot._connection.loop)
    return bot._connection.loop.is_closed()

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name=f"twitch.tv/treezer_"))
    check_free_games.start()
    award_treezcoins_for_vc.start()
    send_economy_file.start()
    check_temporary_roles.start()
    bot.loop.create_task(start_drops())
    print(f'Connecté en tant que {bot.user}!')

def load_emojis(filename='emojis.json'):
    with open(filename, 'r') as file:
        return json.load(file)

emojis = load_emojis()

def load_game_state():
    try:
        with open(GAME_STATE_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {"current_games": []}

def save_game_state(data):
    with open(GAME_STATE_FILE, "w") as file:
        json.dump(data, file, indent=4)

def load_data_noel():
    try:
        with open(NOEL_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_data_noel(data):
    with open(NOEL_FILE, "w") as file:
        json.dump(data, file, indent=4)



def get_emoji(name):
    return emojis.get(name, '')

def load_ticket_data(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_ticket_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def load_data_eco():
    try:
        with open("economie.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def save_data_eco(updated_user_data):
    try:
        with open("economie.json", "r") as file:
            all_data = json.load(file)
    except FileNotFoundError:
        all_data = {}
    except json.JSONDecodeError:
        all_data = {} 

    all_data.update(updated_user_data)

    with open("economie.json", "w") as file:
        json.dump(all_data, file, indent=4)


CONFIG_FILE = "state_raid.json"

join_times = {}
anti_join_enabled = {}

def save_data_raid(data):
    with open("join_times.json", "w") as f:
        clean_data = {
            guild_id: [time for time in times if isinstance(time, str) and time != "enabled"]
            for guild_id, times in data.items()
        }
        json.dump(clean_data, f)


def load_data_raid():
    try:
        with open("join_times.json", "r") as f:
            data = json.load(f)
            for guild_id, times in data.items():
                data[guild_id] = [time for time in times if isinstance(time, str) and time != "enabled"]
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


ANTI_JOIN_FILE = "anti_join_status.json"

def load_anti_join_status():
    """Charge l'état de l'anti-join depuis un fichier JSON."""
    try:
        with open(ANTI_JOIN_FILE, "r") as f:
            data = json.load(f)
            return data.get("anti_join_active", False)
    except FileNotFoundError:
        return False

def save_anti_join_status(status):
    """Sauvegarde l'état de l'anti-join dans un fichier JSON."""
    with open(ANTI_JOIN_FILE, "w") as f:
        json.dump({"anti_join_active": status}, f)

anti_join_active = load_anti_join_status()
#################################### TICKETS  #############################################


@bot.tree.command(name="send_remote_button")
@discord.app_commands.checks.has_permissions(administrator=True)
async def send_remote_button(interaction: discord.Interaction):
    """Envoyer l'embed des ticket + Bouton"""
    embed = discord.Embed(
        title=f"{get_emoji('krown')} Treezer Server Support !",
        description="Pour toutes demandes, veuiillez interagir avec le bouton ci-dessous puis indiquer la raison de vôtre demande"
        )

    view = RemoteButtonView()
    remote_channel = interaction.guild.get_channel(1292944861032484885)
    if remote_channel:
        await remote_channel.send(embed=embed, view=view)
        embed = create_small_embed(f"Panel envoyé avec succès {get_emoji('yes')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = create_small_embed(f"Le salon de télécommande spécifié n'a pas été trouvé {get_emoji('no')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RemoteButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📨 Ouvrir un Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        CATEGORY_ID = 1299809534059216896
        if CATEGORY_ID is None:
            embed = create_small_embed(f"La catégorie pour les tickets n'a pas été configurée {get_emoji('no')}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        category = interaction.guild.get_channel(1299809534059216896)
        if not category or not isinstance(category, discord.CategoryChannel):
            embed = create_small_embed(f"La catégorie spécifiée n'existe pas ou n'est pas valide {get_emoji('no')}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
            get(interaction.guild.roles, id=1292931666377179258): discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
        }
        ticket_channel = await category.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        embed = create_small_embed(f"Ticket créé : {ticket_channel.mention} {get_emoji('IconSupport')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        member=interaction.user

        embed = discord.Embed(
            title=f"Bienvenue dans votre ticket {member.display_name}",
            description="Merci d'avoir ouvert un ticket, Veuillez nous indiquer la raison"
        )

        action_view = TicketActionView(ticket_channel.id, interaction.user.id)

        log_channel = interaction.guild.get_channel(1301143379832475699)
        if log_channel:
            embed2 = create_embed(title='Ouvert', description=f"{ticket_channel.mention} créé par {interaction.user.mention}.", color=0xDFC57B)
            await log_channel.send(embed=embed2)

        await ticket_channel.send(embed=embed, view=action_view)

        ticket_data = {
            "user_id": interaction.user.id,
            "channel_id": ticket_channel.id
        }
        all_tickets = load_ticket_data("ticket.json")
        all_tickets[str(interaction.user.id)] = ticket_data
        save_ticket_data("ticket.json", all_tickets)

class TicketActionView(discord.ui.View):
    def __init__(self, ticket_channel_id, user_id):
        super().__init__(timeout=None)
        self.ticket_channel_id = ticket_channel_id
        self.user_id = user_id

    @discord.ui.button(label="Fermer le Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = get(interaction.guild.roles, id=1292931666377179258)
        if role not in interaction.user.roles:
            small_embed = create_small_embed(f"Vous n'avez pas les permissions pour fermer ce ticket, veuillez annuler votre demande {get_emoji('no')}")
            await interaction.response.send_message(embed=small_embed, ephemeral=True)
            return

        log_channel = interaction.guild.get_channel(1301143379832475699)
        ticket_channel = interaction.guild.get_channel(self.ticket_channel_id)
        if ticket_channel:
            embed_log = create_embed(title="Fermeture", description=f"{ticket_channel.name} fermé par {interaction.user.mention}.", color=0xDFC57B)
            await log_channel.send(embed=embed_log)
            await ticket_channel.delete()
            user = interaction.user
            embed_mp = create_small_embed(f"Ticket fermé avec succès.{get_emoji('yes')}")
            await user.send(embed=embed_mp)

            all_tickets = load_ticket_data("ticket.json")
            if str(self.user_id) in all_tickets:
                del all_tickets[str(self.user_id)]
                save_ticket_data("ticket.json", all_tickets)

    @discord.ui.button(label="Annuler la Demande", style=discord.ButtonStyle.secondary, custom_id="cancel_ticket")
    async def cancel_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            embed_stop = create_small_embed(f"Seul l'utilisateur ayant ouvert le ticket peut annuler la demande {get_emoji('no')}")
            await interaction.response.send_message(embed=embed_stop, ephemeral=True)
            return

        ticket_channel = interaction.guild.get_channel(self.ticket_channel_id)
        if ticket_channel:
            await ticket_channel.delete()
            log_channel = interaction.guild.get_channel(1301143379832475699)
            if log_channel:
                embed_log2 = create_embed(title="Annulation de Ticket", description=f"Ticket {ticket_channel.name} annulé par {interaction.user.mention}.", color=0xB82325)
                user = interaction.user
                await user.send(embed=embed_log2)
                await log_channel.send(embed=embed_log2)

            all_tickets = load_ticket_data("ticket.json")
            if str(self.user_id) in all_tickets:
                del all_tickets[str(self.user_id)]
                save_ticket_data("ticket.json", all_tickets)

################### LOAD #########################

def load_data(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

############################# COMMANDS #######################################

@bot.tree.command()
@discord.app_commands.checks.has_permissions(administrator=True)
async def ban(interaction: discord.Interaction, member: discord.Member, *, raison: str):
    '''Ban'''
    guild = interaction.guild
    embed_ = discord.Embed(
        title=f"{get_emoji('red')} Ban {get_emoji('red')}",
        description=f"Vous avez été banni du serveur Elysiium Faction pour la raison suivante : **{raison}**",
        color=discord.Color.red()
    )
    try:
        await member.send(embed=embed_)
        message = f"{member} à été banni {get_emoji('ww')}"
    except:
        message = f"Le message n'a pas pu être envoyé à {member} mais il a bien été banni"

    await guild.ban(member, reason=raison)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    await log_channel.send(embed=create_small_embed(f'{member.mention} a été ban par {interaction.user.mention} pour {raison}'))

    await interaction.response.send_message(f"{get_emoji('yes_emoji')}", ephemeral=True)

################################# FONCTIONNALITEES #########################################
############ ANTI RAID #################

@bot.tree.command(name="lock_server", description="Verrouille le serveur pour les nouveaux membres")
@discord.app_commands.checks.has_permissions(administrator=True)
async def lock_server(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message(
            "Cette commande doit être exécutée dans un serveur.", ephemeral=True
        )
        return

    try:
        for channel in guild.text_channels:
            overwrite = channel.overwrites_for(guild.default_role)
            overwrite.send_messages = False
            await channel.set_permissions(guild.default_role, overwrite=overwrite)

        await interaction.response.send_message(
            "🔒 Le serveur a été verrouillé avec succès. Les nouveaux membres ne peuvent pas envoyer de messages.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Une erreur est survenue lors du verrouillage : {e}",
            ephemeral=True
        )

@bot.tree.command(name="unlock_server", description="Déverrouille le serveur pour les nouveaux membres")
@discord.app_commands.checks.has_permissions(administrator=True)
async def unlock_server(interaction: discord.Interaction):
    guild = interaction.guild

    if not guild:
        await interaction.response.send_message(
            "Cette commande doit être exécutée dans un serveur.", ephemeral=True
        )
        return

    try:
        for channel in guild.text_channels:
            overwrite = channel.overwrites_for(guild.default_role)
            overwrite.send_messages = None
            await channel.set_permissions(guild.default_role, overwrite=overwrite)

        await interaction.response.send_message(
            "🔓 Le serveur a été déverrouillé avec succès. Les nouveaux membres peuvent à nouveau envoyer des messages.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Une erreur est survenue lors du déverrouillage : {e}",
            ephemeral=True
        )

@bot.tree.command(name="anti_join_on", description="Active l'anti-join pour bloquer les nouveaux membres")
@discord.app_commands.checks.has_permissions(administrator=True)
async def anti_join_on(interaction: discord.Interaction):
    global anti_join_active
    anti_join_active = True
    save_anti_join_status(anti_join_active)
    await interaction.response.send_message(
        "🔒 Anti-join activé ! Les nouveaux membres seront automatiquement expulsés.",
        ephemeral=True
    )

@bot.tree.command(name="anti_join_off", description="Désactive l'anti-join pour permettre les nouveaux membres")
@discord.app_commands.checks.has_permissions(administrator=True)
async def anti_join_off(interaction: discord.Interaction):
    global anti_join_active
    anti_join_active = False
    save_anti_join_status(anti_join_active)
    await interaction.response.send_message(
        "🔓 Anti-join désactivé ! Les nouveaux membres peuvent rejoindre normalement.",
        ephemeral=True
    )

@bot.tree.command(name="enable_antiraid", description="Active le système Anti-Raid.")
@discord.app_commands.checks.has_permissions(administrator=True)
async def enable_antiraid(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)

    try:
        config = load_data_raid()
    except FileNotFoundError:
        config = {}

    config[guild_id] = {"enabled": True}

    save_data_raid(config)

    raid_channel = interaction.guild.get_channel(1306346010917867591)
    if raid_channel:
        await raid_channel.send("🚨 **Anti-Raid activé !** Toutes les activités suspectes seront signalées ici.")
    
    await interaction.response.send_message(
        "Le système Anti-Raid a été activé avec succès ! 🚨",
        ephemeral=True
    )

@bot.tree.command(name="disable_antiraid", description="Désactive le système Anti-Raid.")
@discord.app_commands.checks.has_permissions(administrator=True)
async def disable_antiraid(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)

    try:
        config = load_data_raid()
    except FileNotFoundError:
        config = {}

    if guild_id in config:
        config[guild_id]["enabled"] = False
        save_data_raid(config)

        raid_channel = interaction.guild.get_channel(1306346010917867591)
        if raid_channel:
            await raid_channel.send("❌ **Anti-Raid désactivé !** Les activités suspectes ne seront plus surveillées.")

        await interaction.response.send_message(
            "Le système Anti-Raid a été désactivé avec succès. ❌",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "Le système Anti-Raid n'était pas activé pour ce serveur.",
            ephemeral=True
        )


async def trigger_raid_protection(guild, reason):
    alert_channel = guild.get_channel(1306346010917867591)
    if alert_channel:
        await alert_channel.send(f"⚠️ Détection de RAID : {reason}. Le serveur est verrouillé temporairement.")

    for channel in guild.text_channels:
        overwrite = channel.overwrites_for(guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(guild.default_role, overwrite=overwrite)

    await asyncio.sleep(600)

    for channel in guild.text_channels:
        overwrite = channel.overwrites_for(guild.default_role)
        overwrite.send_messages = None 
        await channel.set_permissions(guild.default_role, overwrite=overwrite)
        
############## ANTI SPAM ################

spam_data=load_data('spam.json')
def get_timeout_duration(spam_count):
    if spam_count == 1:
        return timedelta(minutes=1)
    elif spam_count == 2:
        return timedelta(minutes=10)
    elif spam_count == 3:
        return timedelta(hours=1)
    elif spam_count == 4:
        return timedelta(hours=10)
    elif spam_count == 5:
        return timedelta(days=1)
    else:
        return timedelta(weeks=1)

@bot.tree.command()
@discord.app_commands.checks.has_permissions(administrator=True)
async def spam(interaction, member: discord.Member):
    user_id = str(member.id)
    spam_count = spam_data.get(user_id, 0)
    is_timed_out = member.is_timed_out() 
    timeout_status = "Oui" if is_timed_out else "Non"
    
    embed = discord.Embed(title="Informations sur le spam", color=discord.Color.blue())
    embed.add_field(name="Membre", value=member.mention, inline=True)
    embed.add_field(name="Nombre de spams", value=str(spam_count), inline=True)
    embed.add_field(name="En timeout actuellement", value=timeout_status, inline=True)
    await interaction.response.send_message(embed=embed)
    

########### JEUX GRATUITS ##############

FREE_GAMES_CHANNEL_ID = 1304515694620180542
GAME_STATE_FILE = "game_state.json"


EPIC_GAMES_URL = "https://store.epicgames.com/fr/free-games"

@bot.tree.command(name="recup_games")
async def recup_games(interaction):
    """Commande pour récupérer les jeux gratuits Epic Games"""
    try:
        url = "https://store.epicgames.com/fr/free-games"
        headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.88 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1"
}

        response = requests.get(url, headers=headers)

        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        games = soup.find_all("div", class_="css-1myhtyb")

        if not games:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Aucun jeu trouvé",
                    description="Impossible de récupérer les jeux gratuits pour le moment. Réessayez plus tard.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        for game in games[:2]:
            title = game.find("span", class_="css-2ucwu").text.strip()
            availability = game.find("span", class_="css-119zqjf").text.strip()
            period = game.find("span", class_="css-1sclytn").text.strip() if game.find("span", class_="css-1sclytn") else "Non disponible"

            embed = discord.Embed(
                title=f"🎮 {title}",
                description=f"Disponibilité : **{availability}**\nPériode : **{period}**",
                color=discord.Color.blue(),
            )
            image_url = game.find("img")["src"] if game.find("img") else None
            if image_url:
                embed.set_image(url=image_url)

            await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Erreur",
                description=f"Une erreur est survenue lors de la récupération des jeux : {e}",
                color=discord.Color.red(),
            ),
            ephemeral=True,
        )

async def fetch_free_games():
    async with aiohttp.ClientSession() as session:
        async with session.get(EPIC_GAMES_URL) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            free_games = []
            game_containers = soup.find_all("div", class_="css-1myhtyb")
            for container in game_containers[:2]:
                title = container.find("span", class_="css-2ucwu").text
                status = container.find("div", class_="css-1txuvy0").text.strip()
                period = container.find("div", class_="css-15g5ncy").text if status == "Gratuit" else None

                free_games.append({
                    "title": title,
                    "status": status,
                    "period": period
                })

            return free_games

@tasks.loop(hours=1)
async def check_free_games():
    current_state = load_game_state()

    free_games = await fetch_free_games()

    new_games = []
    for game in free_games:
        if game["title"] not in current_state["current_games"]:
            new_games.append(game)
            current_state["current_games"].append(game["title"])

    save_game_state(current_state)

    channel = bot.get_channel(FREE_GAMES_CHANNEL_ID)
    for game in new_games:
        description = f"Statut : {game['status']}\n"
        if game["period"]:
            description += f"Disponible du {game['period']}"
        else:
            description += "Non disponible pour le moment."
        embed = Embed(
            title=f"🎮 {game['title']}",
            description=description,
            color=0x00ff00 if game["status"] == "Gratuit" else 0xff0000
        )
        await channel.send(embed=embed)

################ VOC #################

TREEZCOINS_REWARD = 80
CHECK_INTERVAL = 60
MINUTES_THRESHOLD = 5
GUILD_ID = 1272525476103065733
VC_COIN_CHANNEL_ID = 1301093110717087784

@tasks.loop(seconds=CHECK_INTERVAL)
async def award_treezcoins_for_vc():
    try:
        with open('voc.json', 'r') as f:
            voc_data = json.load(f)
        with open('economie.json', 'r') as f:
            economie_data = json.load(f)
    except FileNotFoundError:
        voc_data = {}
        economie_data = {}

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    current_date_key = str(datetime.now().date())
    if current_date_key not in voc_data:
        voc_data[current_date_key] = {}

    for channel in guild.voice_channels:
        if len(channel.members) > 1:
            for member in channel.members:
                if not member.bot:

                    member_id = str(member.id)
                    voc_data[current_date_key][member_id] = voc_data[current_date_key].get(member_id, 0) + 1

                    if voc_data[current_date_key][member_id] >= MINUTES_THRESHOLD:
                        if member_id in economie_data:
                            economie_data[member_id]["coins"] += TREEZCOINS_REWARD
                        else:
                            economie_data[member_id] = {"coins": TREEZCOINS_REWARD, "xp": 0, "level": 0}

                        voc_data[current_date_key][member_id] = 0

                        vc_log_channel = guild.get_channel(VC_COIN_CHANNEL_ID)
                        if vc_log_channel:
                            embed = discord.Embed(
                                title="Treezcoins Awarded",
                                description=f"{member.mention} a reçu {TREEZCOINS_REWARD} Treezcoins pour {MINUTES_THRESHOLD} minutes en vocal.",
                                color=discord.Color.green()
                            )
                            await vc_log_channel.send(embed=embed)

                        with open('economie.json', 'w') as f:
                            json.dump(economie_data, f, indent=4)

    with open('voc.json', 'w') as f:
        json.dump(voc_data, f, indent=4)
        
                  ################# STATS ######################
"""
TIKTOK_USERNAME = "ilian_amd"
STATS_FILE = "stats.json"
api = TikTokApi(custom_verify_fp="2mAAPwZuIm9DQuW2Y1v07FSzZEj", use_test_endpoints=True)

def load_stats():
    if not os.path.exists(STATS_FILE):
        with open(STATS_FILE, "w") as file:
            json.dump({"tiktok_channel_id": None}, file)
    with open(STATS_FILE, "r") as file:
        return json.load(file)

def save_stats(data):
    with open(STATS_FILE, "w") as file:
        json.dump(data, file)

stats = load_stats()

try:
    api = TikTokApi(custom_verify_fp="2mAAPwZuIm9DQuW2Y1v07FSzZEj", use_test_endpoints=True)
except Exception as e:
    print(f"Erreur lors de l'initialisation de l'API TikTok : {e}")

async def get_tiktok_follower_count():
    try:
        user_info = await api.user(username="ilian_amd").info()
        follower_count = user_info["stats"]["followerCount"]
        return follower_count
    except Exception as e:
        print(f"Erreur lors de la récupération du nombre d'abonnés TikTok : {e}")
        return None

@bot.tree.command(name="creer_salon_abonnes", description="Crée un salon vocal pour afficher les abonnés TikTok.")
@discord.app_commands.checks.has_permissions(administrator=True)
async def creer_salon_abonnes(interaction: discord.Interaction):
    guild = interaction.guild

    tiktok_follower_count = await get_tiktok_follower_count()
    tiktok_channel_name = f"Abonnés TikTok : {tiktok_follower_count}"
    tiktok_channel = await guild.create_voice_channel(name=tiktok_channel_name, category=guild.get_channel(1276554503700742307))
    stats["tiktok_channel_id"] = tiktok_channel.id

    save_stats(stats)
    await interaction.response.send_message("Salon vocal créé pour suivre les abonnés TikTok.", ephemeral=True)

@tasks.loop(minutes=10)
async def update_follower_channels():
    guild = bot.get_guild(DISCORD_GUILD_ID)

    tiktok_channel = guild.get_channel(stats["tiktok_channel_id"])
    tiktok_follower_count = await get_tiktok_follower_count()
    if tiktok_channel and tiktok_follower_count is not None:
        await tiktok_channel.edit(name=f"Abonnés TikTok : {tiktok_follower_count}")"""

    
                  ################ ECONOMIE ####################
        
@bot.tree.command(name="manual_backup", description="Envoie une sauvegarde manuelle du fichier économie dans un salon.")
@discord.app_commands.checks.has_permissions(administrator=True)
async def manual_backup(interaction: discord.Interaction):
    try:
        file_path = "economie.json"  
        with open(file_path, "rb") as file:
            channel = bot.get_channel(1312760681610739733)

            if channel:
                await channel.send(content="Voici la sauvegarde actuelle du fichier économie :", file=discord.File(file, "economie.json"))
                await interaction.response.send_message("Le fichier `economie.json` a été envoyé dans le salon spécifié.", ephemeral=True)
            else:
                await interaction.response.send_message("Erreur : Le salon n'a pas été trouvé.", ephemeral=True)
    except FileNotFoundError:
        await interaction.response.send_message("Erreur : Le fichier `economie.json` est introuvable.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Erreur inattendue : {e}", ephemeral=True)
        
					########### DROP ###################

DROP_CHANNEL_ID = 1303428340866093146
DROP_FILE = "drop.json"
ECONOMY_FILE = "economie.json"

class Drop(discord.ui.View):
    def __init__(self, winners, message_id):
        super().__init__(timeout=None)
        self.winners = winners
        self.message_id = message_id

    @discord.ui.button(label="Recuperer la money !", style=discord.ButtonStyle.green, custom_id='recupmoney')
    async def grab_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)

        if user_id in self.winners:
            await interaction.response.send_message(
                embed=create_small_embed("Vous ne pouvez participer qu'une fois à un drop !"), 
                ephemeral=True
            )
            return

        position = len(self.winners)
        if position == 0:
            reward = 1000
            medal = "🥇"
        elif position == 1:
            reward = 500
            medal = "🥈"
        elif position == 2:
            reward = 250
            medal = "🥉"
            button.disabled = True
        else:
            await interaction.response.send_message(
                embed=create_small_embed("Le drop est déjà complet !"), 
                ephemeral=True
            )
            return

        self.winners.append(user_id)

        economie=load_data_eco()

        previous_balance = economie.get(user_id, {}).get("coins", 0)
        if user_id in economie:
            economie[user_id]["coins"] += reward
        else:
            economie[user_id] = {"coins": reward}

        with open(ECONOMY_FILE, 'w') as f:
            json.dump(economie, f, indent=4)

        log_channel = bot.get_channel(1303789058400583682)
        new_balance = economie[user_id]["coins"]
        await log_channel.send(
            embed=create_embed(
                title="Log de Drop",
                description=f"{interaction.user.mention} a participé au drop et a gagné {reward} Treezcoins {medal}!\n"
                            f"Solde précédent : {previous_balance} coins\nNouveau solde : {new_balance} coins"
            )
        )

        await interaction.response.edit_message(
            embed=create_embed(
                title='Drop !',
                description=f"Cliquez en premier sur le bouton pour gagner des treezcoins !\n"
                            f"Récompenses :\n1er: 1000 coins 🥇\n2ème: 500 coins 🥈\n3ème: 250 coins 🥉\n"
                            f"Gagnants : {self.format_winners()}",
            ),
            view=self
        )

        self.update_drop_file()

    def format_winners(self):
        medals = ["🥇", "🥈", "🥉"]
        return ", ".join([f"{medals[i]} <@{uid}>" for i, uid in enumerate(self.winners)])

    def update_drop_file(self):
        drop_data = {
            "message_id": self.message_id,
            "winners": self.winners
        }
        with open(DROP_FILE, 'w') as f:
            json.dump(drop_data, f, indent=4)

async def start_drops():
    while True:
        await asyncio.sleep(random.randint(36000, 64800))
        await launch_drop()

async def launch_drop():
    channel = bot.get_channel(DROP_CHANNEL_ID)
    if channel:
        message = await channel.send(
            embed=create_embed(
                title='Drop !',
                description="Cliquez en premier sur le bouton pour gagner des treezcoins !\n"
                            "Récompenses :\n1er: 1000 coins 🥇\n2ème: 500 coins 🥈\n3ème: 250 coins 🥉"
            ),
            view=Drop([], None)
        )
        drop_view = Drop([], message.id)
        drop_view.update_drop_file()

        log_channel = bot.get_channel(1303789058400583682)
        await log_channel.send(
            embed=create_embed(
                title="Drop lancé",
                description=f"Un nouveau drop a été lancé dans {channel.mention} à {datetime.now().strftime('%H:%M:%S')}."
            )
        )

@bot.tree.command(name="forcedrop", description="Forcer un drop")
@discord.app_commands.checks.has_permissions(administrator=True)
async def forcedrop(interaction):
    await launch_drop()
    await interaction.response.send_message("Drop forcé lancé avec succès !", ephemeral=True)

user_messages = {}
economy_data = load_data_eco()

@bot.tree.command(name="reset")
@discord.app_commands.checks.has_permissions(administrator=True)
async def reset(interaction, user: discord.User):
    user_id = str(user.id)
    economy_data = load_data_eco()

    if user_id in economy_data:
        economy_data[user_id] = {"coins": 0, "xp": 0, "level": 0}
        save_data_eco(economy_data)
        await interaction.response.send_message(f"Les statistiques de {user.mention} ont été réinitialisées à 0.")
    else:
        await interaction.response.send_message(f"{user.mention} n'a pas de statistiques enregistrées.")

link_pattern = re.compile(r"(https?://|www\.)\S+")
raid_alert_threshold = {
    "joins": 5,
    "messages": 10,
    "time_window_joins": timedelta(minutes=1),
    "time_window_messages": 7
}

join_history = {}
message_counts = {} 


@bot.event
async def on_message(message):
    await bot.process_commands(message)
    ignored_channels = [1272533485030080583, 1272534627583655946]
    if message.channel.id in ignored_channels:
        return

    if message.author.bot:
        return 
    exempt_roles = [
        1292930841286021210, 1292931666377179258, 1301602510557020190,
        1292931931050348574, 1292936072095076456, 1292935044901371924
    ]

    user_id = message.author.id
    guild_id = message.guild.id
    now = datetime.utcnow()

    if guild_id not in message_counts:
        message_counts[guild_id] = {}
    if user_id not in message_counts[guild_id]:
        message_counts[guild_id][user_id] = []

    message_counts[guild_id][user_id].append(now)

    message_counts[guild_id][user_id] = [
        msg_time for msg_time in message_counts[guild_id][user_id]
        if now - msg_time < timedelta(seconds=raid_alert_threshold["time_window_messages"])
    ]

    if len(message_counts[guild_id][user_id]) > raid_alert_threshold["messages"]:
        await trigger_raid_protection(message.guild, f"Spamming détecté par {message.author.mention}")
        await message.author.ban(reason="Détection de raid : spam de messages")
        message_counts[guild_id][user_id] = []

    if link_pattern.search(message.content):
        if not any(role.id in exempt_roles for role in message.author.roles):
            log_channel = bot.get_channel(1301664284102758430)
            try:
                await message.author.timeout(timedelta(hours=1), reason="Lien détecté")
            except discord.Forbidden:
                pass

            embed = discord.Embed(title="Lien détecté et supprimé", color=discord.Color.red())
            embed.add_field(name="Membre", value=message.author.mention, inline=True)
            embed.add_field(name="Action", value="Timeout de 1 heure", inline=False)
            embed.add_field(name="Message supprimé", value=message.content, inline=False)
            await log_channel.send(embed=embed)
            await message.delete()

    user_id = str(message.author.id)
    now = datetime.utcnow()
    user_messages[user_id] = [msg_time for msg_time in user_messages.get(user_id, []) if now - msg_time < timedelta(minutes=1)]
    user_messages[user_id].append(now)

    if len(user_messages[user_id]) >= 10:
        spam_data[user_id] = spam_data.get(user_id, 0) + 1
        timeout_duration = get_timeout_duration(spam_data[user_id])

        try:
            await message.author.timeout(timeout_duration, reason="Spam détecté")
        except discord.Forbidden:
            pass

        log_channel = bot.get_channel(1301664792586752051)
        embed = discord.Embed(title="Action anti-spam", color=discord.Color.red())
        embed.add_field(name="Membre", value=message.author.mention, inline=True)
        embed.add_field(name="Raison", value=f"Spam détecté (10 messages en moins d'une minute)", inline=False)
        embed.add_field(name="Action", value=f"Timeout de {timeout_duration}", inline=False)
        embed.add_field(name="Nombre de spams", value=str(spam_data[user_id]), inline=False)
        await log_channel.send(embed=embed)

        user_messages[user_id] = []
        save_data_eco(spam_data, "spam.json")

    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 1})
    user_data["coins"] += 120
    economy_data[user_id] = user_data
    await update_level(message.author, user_data)
    save_data_eco(economy_data)
roles = {
    1: 1298591387469484073,
    10: 1298591387477999668,
    25: 1298591388279242823,
    50: 1298591389164113983,
    75: 1298592077713768448,
    100: 1298592254184656896,
}

async def update_level(member, user_data):
    xp_needed = 1000

    while user_data["xp"] >= xp_needed:
        user_data["level"] += 1
        user_data["xp"] -= xp_needed
        economy_data = load_data_eco()
        economy_data[str(member.id)] = user_data
        save_data_eco(economy_data)

        if user_data["level"] in roles:
            role = member.guild.get_role(roles[user_data["level"]])
            if role and role not in member.roles:
                await member.add_roles(role)
                embed = Embed(
                    title="🎉 Rankup",
                    description=f"Félicitations à {member.mention} ! Vous avez atteint le niveau {user_data['level']} !",
                    color=0x131fd1
                )
                file = File("update_level_banner.png", filename="update_level_banner.png")
                embed.set_image(url="attachment://update_level_banner.png")

                rankup_channel = member.guild.get_channel(rankup_channel_id)
                await rankup_channel.send(embed=embed, file=file)

                log_channel = member.guild.get_channel(log_channel_id)
                if log_channel:
                    log_embed = Embed(
                        title="Nouveau Rankup",
                        description=f"{member.mention} est passé au niveau {user_data['level']}.",
                        color=discord.Color.green()
                    )
                    await log_channel.send(embed=log_embed)
    
@bot.tree.command(name="rankup", description="Améliorez votre niveau si vous avez assez d'XP.")
async def rankup(interaction):
    user_id = str(interaction.user.id)
    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 0})
    if user_data["xp"] >= 1000:
        await update_level(interaction.user, user_data)
        economy_data[user_id] = user_data
        save_data_eco(economy_data)
        embed = discord.Embed(description="Vous avez amélioré votre niveau avec succès !", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(description="Vous n'avez pas assez d'XP pour passer au niveau suivant.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

ECONOMY_FILE = "economie.json"
CATEGORY_CHANNEL_ID = 1305234992896540774

categories = {
    "animation": {
        "Choix animation": {"price": 25000, "role_id": 1305203860117258361},
        "Pass prioritaire": {"price": 20000, "role_id": 1305204544149393439},
        "Animation entre VIP": {"price": 50000, "role_id": 1305204084093091942}
    },
    "roles": {
        "L'ancien en personne": {"price": 75000, "role_id": 1305200094231924736},
        "le/a sous goat du serveur": {"price": 50000, "role_id": 1305200344380215346},
        "la famille": {"price": 35000, "role_id": 1305200474462617692},
        "le/a reuf du serveur": {"price": 25000, "role_id": 1305200584457981974}
    },
    "xp": {
        "550 XP": {"price": 5000, "xp": 550},
        "1150 XP": {"price": 11000, "xp": 1150},
        "2500 XP": {"price": 20000, "xp": 2500},
        "5000 XP": {"price": 35000, "xp": 5000},
        "7000 XP": {"price": 50000, "xp": 7000}
    },
    "concept": {
        "Choisir un concept": {"price": 40000, "role_id": 1301225106990694455},
        "Jury avec Treezer": {"price": 50000, "role_id": 1305202855267012648},
        "Jeux avec Treezer": {"price": 55000, "role_id": 1305202680573984788},
        "Choix jeux": {"price": 25000, "role_id": 1305202984111702026}
    }
}

class CategorySelectView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategorySelect())

class CategorySelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Animation hors live", value="animation"),
            discord.SelectOption(label="Roles", value="roles"),
            discord.SelectOption(label="XP", value="xp"),
            discord.SelectOption(label="Concept", value="concept"),
        ]
        super().__init__(placeholder="Choisissez une catégorie...", min_values=1, max_values=1, options=options, custom_id="category_select")

    async def callback(self, interaction: discord.Interaction):
        selected_category = self.values[0]
        embed = discord.Embed(title=f"Shop - {selected_category.capitalize()}",
                              description=f"Sélectionnez un article dans la catégorie **{selected_category.capitalize()}** {get_emoji('whitefire')}",
                              color=0xbd2bda)
        await interaction.response.send_message(embed=embed, view=ItemSelectView(selected_category), ephemeral=True)

class ItemSelectView(View):
    def __init__(self, category):
        super().__init__(timeout=None)
        self.add_item(ItemSelect(category))

class ItemSelect(Select):
    def __init__(self, category):
        options = [
            discord.SelectOption(label=item_name, description=f"{item_data['price']} TreezCoins 🪙", value=item_name)
            for item_name, item_data in categories[category].items()
        ]
        super().__init__(placeholder="Choisissez un article...", min_values=1, max_values=1, options=options, custom_id="item_select")
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        item_name = self.values[0]
        item = categories[self.category][item_name]

        economy_data = load_data_eco()
        user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 1})
        user_coins_before = user_data["coins"]

        if user_data["coins"] >= item["price"]:
            user_data["coins"] -= item["price"]

            if "xp" in item:
                user_data["xp"] += item["xp"]
                await update_level(interaction.user, user_data)
                embedachat = discord.Embed(
                    title="Achat Réussi",
                    description=f"Vous avez acheté **{item_name}** pour {item['price']} TreezCoins !\nVous avez gagné {item['xp']} XP. {get_emoji('star')}",
                    color=0xbd2bda
                )
                await interaction.response.send_message(embed=embedachat, ephemeral=True)
            elif "role_id" in item:
                role = interaction.guild.get_role(item["role_id"])
                if role:
                    await interaction.user.add_roles(role)
                    embedachat = discord.Embed(
                        title="Achat Réussi",
                        description=f"Vous avez acheté le rôle **{item_name}** pour {item['price']} TreezCoins {get_emoji('krown')}!",
                        color=0xbd2bda
                    )
                    await interaction.response.send_message(embed=embedachat, ephemeral=True)

            economy_data[user_id] = user_data
            save_data_eco(economy_data)

            log_channel = interaction.guild.get_channel(CATEGORY_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="Log d'Achat dans le Shop",
                    color=0xbd2bda
                )
                log_embed.add_field(name="Membre", value=interaction.user.mention, inline=False)
                log_embed.add_field(name="Article", value=item_name, inline=True)
                log_embed.add_field(name="Prix", value=f"{item['price']} TreezCoins", inline=True)
                log_embed.add_field(name="Solde avant achat", value=f"{user_coins_before} TreezCoins", inline=True)
                log_embed.add_field(name="Solde après achat", value=f"{user_data['coins']} TreezCoins", inline=True)
                log_embed.add_field(name="Date", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
                await log_channel.send(embed=log_embed)
        else:
            embedachat = discord.Embed(
                title="Achat Refusé ❕",
                description=f"Vous n'avez pas assez de TreezCoins pour cet article. {get_emoji('no')}",
                color=0xbd2bda
            )
            await interaction.response.send_message(embed=embedachat, ephemeral=True)

@bot.tree.command(name="shop")
async def shop(interaction):
    embed = discord.Embed(
        title="Bienvenue dans le Shop",
        description="Sélectionnez une catégorie d'articles à acheter :",
        color=0xbd2bda
    )
    await interaction.response.send_message(embed=embed, view=CategorySelectView())

@bot.tree.command(name="treezcoins")
async def treezcoins(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    economy_data = load_data_eco()
    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 0})

    embed = Embed(title="Vos informations TreezCoins", color=0x00ff00)
    embed.add_field(name="TreezCoins", value=f"{user_data['coins']} coins 🪙", inline=False)
    embed.add_field(name="XP", value=f"{user_data['xp']} XP 💥", inline=False)
    embed.add_field(name="Niveau", value=f"Niveau {user_data['level']} 🔢", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tasks.loop(hours=1)
async def check_temporary_roles():
    current_time = datetime.utcnow()
    for user_id, role_data in list(economy_data.get("temporary_roles", {}).items()):
        expiration_date = datetime.fromisoformat(role_data["expiration_date"])
        if current_time >= expiration_date:
            guild = bot.get_guild(1300097097814507542)
            user = guild.get_member(int(user_id))
            role = guild.get_role(role_data["role_id"])
            if user and role:
                await user.remove_roles(role)
            del economy_data["temporary_roles"][user_id]
    save_data_eco(economy_data)
    
@bot.tree.command(name="treezinfo", description="Affiche les informations TreezCoins d'un membre.")
@discord.app_commands.checks.has_permissions(administrator=True)
async def treezinfo(interaction: discord.Interaction, member: discord.Member):
    user_id = str(member.id)
    
    try:
        with open('economie.json', 'r') as f:
            economy_data = json.load(f)
    except FileNotFoundError:
        economy_data = {}

    if user_id in economy_data:
        user_data = economy_data[user_id]
    else:
        user_data = {"coins": 0, "xp": 0, "level": 0}

    embed = discord.Embed(
        title=f"Informations TreezCoins de {member.display_name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="TreezCoins", value=f"{user_data['coins']} coins", inline=False)
    embed.add_field(name="XP", value=f"{user_data['xp']} XP", inline=False)
    embed.add_field(name="Niveau", value=f"Niveau {user_data['level']}", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

##################### NOEL ###########################

REWARDS = {
    1: {"xp": 1000},
    2: {"coins": 1000},
    3: {"xp": 200},
    4: {"coins": 1000},
    5: {"roles": [1307457111445344377]},
    6: {"xp": 300},
    7: {"coins": 1250},
    8: {"xp": 300},
    9: {"coins": 1250},
    10: {"xp": 500, "coins": 2500},
    11: {"xp": 400},
    12: {"coins": 1500},
    13: {"xp": 400},
    14: {"coins": 500},
    15: {"chance_roles": {1305203860117258361: 20}, "roles": [1307457581203066932]},
    16: {"xp": 500},
    17: {"coins": 2000},
    18: {"xp": 500},
    19: {"coins": 2000},
    20: {"xp": 1000, "coins": 3000, "roles": [1307458296101212180]},
    21: {"xp": 600},
    22: {"coins": 2500},
    23: {"xp": 600},
    24: {"coins": 2500},
    25: {"xp": 2000, "coins": 5000, "chance_roles": {1305202855267012648: 10}, "roles": [1307458521335468153]}
}
async def handle_rewards(member: discord.Member, day: int):
    data_noel = load_data_noel()
    
    if str(member.id) not in data_noel:
        data_noel[str(member.id)] = {"claimed": [], "xp": 0, "coins": 0, "level": 1}

    if day in data_noel[str(member.id)]["claimed"]:
        embed = discord.Embed(
            description=f"🎄 Vous avez déjà récupéré la récompense pour le jour {day}.",
            color=discord.Color.red()
        )
        return embed

    current_date = datetime.utcnow().day
    if current_date != day:
        embed = discord.Embed(
            description=f"⏳ Ce n'est pas encore le jour {day} ! Reviens le bon jour pour récupérer ta récompense.",
            color=discord.Color.orange()
        )
        return embed

    reward = REWARDS.get(day, {})
    response_message = ""

    all_economy_data = load_data_eco()
    user_data = all_economy_data.get(str(member.id), {"xp": 0, "coins": 0, "level": 1})

    if "xp" in reward:
        xp = reward["xp"]
        user_data["xp"] += xp
        response_message += f"🧠 +{xp} XP\n"

    if "coins" in reward:
        coins = reward["coins"]
        user_data["coins"] = user_data.get("coins", 0) + coins
        response_message += f"💰 +{coins} coins\n"

    if "roles" in reward:
        for role_id in reward["roles"]:
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role)
                response_message += f"📜 Rôle ajouté : {role.name}\n"

    if "chance_roles" in reward:
        for role_id, chance in reward["chance_roles"].items():
            role = member.guild.get_role(role_id)
            if role:
                if random.randint(1, 100) <= chance:
                    await member.add_roles(role)
                    response_message += f"🍀 Félicitations ! Vous avez obtenu le rôle : {role.name}\n"
                else:
                    response_message += f"❌ Pas de chance ! Vous n'avez pas obtenu le rôle spécial.\n"

    await update_level(member, user_data)

    data_noel[str(member.id)]["claimed"].append(day)
    save_data_noel(data_noel)

    all_economy_data[str(member.id)] = user_data
    save_data_eco(all_economy_data)

    log_channel = member.guild.get_channel(1312761589312520233)
    if log_channel:
        await log_channel.send(
            f"🎁 {member.name} ({member.id}) a récupéré sa récompense pour le jour {day} !"
        )

    reward_list = ""
    if "xp" in reward:
        reward_list += f"🧠 {reward['xp']} XP\n"
    if "coins" in reward:
        reward_list += f"💰 {reward['coins']} coins\n"
    if "roles" in reward:
        for role_id in reward["roles"]:
            role = member.guild.get_role(role_id)
            if role:
                reward_list += f"📜 Rôle : {role.name}\n"
    if "chance_roles" in reward:
        for role_id, chance in reward["chance_roles"].items():
            role = member.guild.get_role(role_id)
            if role:
                reward_list += f"🍀 Rôle spécial : {role.name} ({chance}% de chance)\n"

    embed = discord.Embed(
        title=f"🎁 **Récompense du jour {day}** 🎁",
        description=f"Voici votre récompense pour aujourd'hui :\n\n{reward_list}\n{response_message}",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Récompense récupérée à {datetime.utcnow().strftime('%H:%M:%S')} UTC")
    return embed



class AdventCalendarView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AdventButton())

class AdventButton(Button):
    def __init__(self):
        super().__init__(
            label="Récupérer la récompense",
            style=ButtonStyle.red,
            custom_id="advent_claim"
        )

    async def callback(self, interaction: discord.Interaction):
        day = datetime.utcnow().day
        member = interaction.user
        data = load_data_noel()
        economy_data = load_data_eco()

        if str(member.id) in data and day in data[str(member.id)]["claimed"]:
            await interaction.response.send_message(
                embed=Embed(
                    description=f"⏳ Vous avez déjà récupéré votre récompense pour le jour {day} !",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        if day not in REWARDS:
            await interaction.response.send_message(
                embed=Embed(
                    description="🎁 Pas de récompense disponible aujourd'hui. Revenez un autre jour !",
                    color=discord.Color.orange()
                ),
                ephemeral=True
            )
            return
        reward_embed = await handle_rewards(member, day)
        await interaction.response.send_message(embed=reward_embed, ephemeral=True)

@bot.tree.command(name="calendrier", description="Afficher le calendrier de l'avent.")
@discord.app_commands.checks.has_permissions(administrator=True)
async def send_calendrier(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎄 Calendrier de l'Avent 🎄",
        description="Clique sur le bouton ci-dessous pour récupérer ta récompense du jour. 🧑‍🎄",
        color=discord.Color.green()
    )
    file = discord.File("sapin_noel.png", filename="sapin_noel.png")
    embed.set_image(url="attachment://sapin_noel.png")

    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(label=f"Récupérer la récompense 🍭", style=discord.ButtonStyle.green, custom_id="claim_reward")
    )

    await interaction.response.send_message(embed=embed, view=view, file=file)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if "custom_id" not in interaction.data:
        return

    custom_id = interaction.data["custom_id"]
    if custom_id == "claim_reward":
        current_day = datetime.utcnow().day
        reward_embed = await handle_rewards(interaction.user, current_day)
        await interaction.response.send_message(embed=reward_embed, ephemeral=True)

###################### BACK - UP ##########################

@tasks.loop(hours=1)
async def send_economy_file():
    channel = bot.get_channel(1312760681610739733)
    if channel:
        await channel.send("📂 Voici le fichier `economie.json` :", file=discord.File("economie.json"))

@send_economy_file.before_loop
async def before_send_economy_file():
    await bot.wait_until_ready()

############ VOCAUX TEMPO ##############

VOICE_TRIGGER_CHANNEL_ID = 1301145722296602705
LOG_CHANNEL_ID = 1301093110717087784
JSON_FILE = "vocal.json"
def load_voice_channels():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r') as file:
            return json.load(file)
    return {}
def save_voice_channels(data):
    with open(JSON_FILE, 'w') as file:
        json.dump(data, file)
temporary_voice_channels = load_voice_channels()
@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    LOG_VOCAL = 1301093110717087784
    log_channel = bot.get_channel(LOG_VOCAL)
    if log_channel is not None:
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title=f"Join {get_emoji('Online')}",
                description =f"{member.mention} a rejoint le salon vocal {after.channel.name}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            await log_channel.send(embed=embed)
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title=f"Leave {get_emoji('Offline')}",
                description=f"{member.mention} a quitté le salon vocal {before.channel.name}",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            await log_channel.send(embed=embed)
    else:
        print(f"Erreur : Le salon de logs avec l'ID {LOG_CHANNEL_ID} n'a pas été trouvé.")
    global temporary_voice_channels
    guild = member.guild
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    
    if after.channel and after.channel.id == VOICE_TRIGGER_CHANNEL_ID:
        category = after.channel.category
        voice_channel_name = f"Salon de {member.display_name}"
        overwrites = {role: perms for role, perms in after.channel.overwrites.items()}
        
        temp_channel = await guild.create_voice_channel(
            name=voice_channel_name,
            category=category,
            overwrites=overwrites
        )
        
        await member.move_to(temp_channel)
        
        temporary_voice_channels[temp_channel.id] = {
            "owner": member.id,
            "channel_id": temp_channel.id
        }
        save_voice_channels(temporary_voice_channels)
        
        if log_channel:
            embed = Embed(
                title="Création de salon vocal",
                description=f"{member.display_name} a rejoint le salon vocal `{after.channel.name}`, un nouveau salon `{voice_channel_name}` a été créé.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

    for channel_id, data in list(temporary_voice_channels.items()):
        temp_channel = guild.get_channel(data["channel_id"])
        if temp_channel and before.channel and temp_channel.id == before.channel.id and len(before.channel.members) == 0:
            await temp_channel.delete()
            del temporary_voice_channels[channel_id]
            save_voice_channels(temporary_voice_channels)
            
            if log_channel:
                embed = Embed(
                    title="Suppression de salon vocal",
                    description=f"Le salon vocal temporaire `{temp_channel.name}` a été supprimé car il est vide.",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                await log_channel.send(embed=embed)

log_channel_coins_id = 1301098651678019584
rankup_channel_id = 1302369087095046184
log_channel_xp_id = 1302716998983221298

@bot.tree.command(name="addcoins")
@discord.app_commands.checks.has_permissions(administrator=True)
async def addcoins(interaction: discord.Interaction, member: discord.Member, quantité: int):
    if quantité <= 0:
        await interaction.response.send_message("La quantité de TreezCoins doit être positive.", ephemeral=True)
        return

    economy_data = load_data_eco()
    user_id = str(member.id)
    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 0})

    user_data["coins"] += quantité
    economy_data[user_id] = user_data
    save_data_eco(economy_data)

    log_channel = bot.get_channel(log_channel_id)
    embed_log = Embed(
        title="Ajout de TreezCoins",
        description=f"{interaction.user.mention} a ajouté {quantité} TreezCoins à {member.mention}.",
        color=discord.Color.blue()
    )
    await log_channel.send(embed=embed_log)
    await interaction.response.send_message(f"{quantité} TreezCoins ajoutés à {member.mention}.", ephemeral=True)

@bot.tree.command(name="addxp")
@discord.app_commands.checks.has_permissions(administrator=True)
async def addxp(interaction: discord.Interaction, member: discord.Member, quantité: int):
    if quantité <= 0:
        await interaction.response.send_message("La quantité d'XP doit être positive.", ephemeral=True)
        return

    economy_data = load_data_eco()
    user_id = str(member.id)
    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 0})

    initial_level = user_data["level"]
    user_data["xp"] += quantité
    await update_level(member, user_data)

    log_channel = bot.get_channel(log_channel_id)
    if log_channel:
        embed_log = Embed(
            title="Ajout d'XP",
            description=(f"{interaction.user.mention} a ajouté {quantité} XP à {member.mention}.\n"
                         f"Level initial: {initial_level}\nLevel actuel: {user_data['level']}"),
            color=discord.Color.green()
        )
        await log_channel.send(embed=embed_log)

    await interaction.response.send_message(f"{quantité} XP ajoutés à {member.mention}.", ephemeral=True)

    
################### MODERATION #################

LOG_WARN_CHANNEL_ID = 1301664284102758430
LOG_SPAM_CHANNEL_ID = 1301664792586752051

def load_warnings():
    try:
        with open("warn.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_warnings(data):
    with open("warn.json", "w") as file:
        json.dump(data, file, indent=4)

warnings = load_warnings()


@bot.tree.command()
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction, member: discord.Member, *, reason: str):
    warn_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    author = interaction.user.name


    user_id = str(member.id)
    if user_id not in warnings:
        warnings[user_id] = []
    warnings[user_id].append({
        "reason": reason,
        "date": warn_date,
        "author": author
    })
    save_warnings(warnings)

    try:
        embedmp = create_small_embed(f"Vous avez reçu un avertissement pour la raison suivante : {reason}")
        await member.send(embed=embedmp, ephemeral=True)
    except discord.Forbidden:
        embedmp2 = create_small_embed(f"Impossible d'envoyer un message privé à {member.mention}.")
        await interaction.response.send_message(embed=embedmp2, ephemeral=True)

    log_channel = bot.get_channel(1301664284102758430)
    embed = discord.Embed(title="Avertissement", color=discord.Color.red())
    embed.add_field(name="Membre", value=member.mention, inline=True)
    embed.add_field(name="Auteur de l'avertissement", value=author, inline=True)
    embed.add_field(name="Raison", value=reason, inline=False)
    embed.add_field(name="Date", value=warn_date, inline=False)
    await log_channel.send(embed=embed)

    await interaction.response.send_message(f"{member.mention} a été averti pour : {reason}", ephemeral=True)
    
@bot.tree.command(name="warn_list")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def warn_list(interaction, member: discord.Member):
    user_id = str(member.id)
    if user_id in warnings and warnings[user_id]:
        embed = discord.Embed(title=f"Avertissements pour {member}", color=discord.Color.orange())
        for idx, warn in enumerate(warnings[user_id], start=1):
            embed.add_field(name=f"Avertissement {idx}",
                            value=f"**Raison** : {warn['reason']}\n**Date** : {warn['date']}\n**Auteur** : {warn['author']}",
                            inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"{member.mention} n'a aucun avertissement.", True)

################################## LOG SYSTEM #######################################

@bot.listen("log_system")
async def log_system(message):
    LOG_MESSAGE = 1301093052206551061
    if message.author.bot:
        return 
    log_channel = bot.get_channel(LOG_MESSAGE)
    if log_channel is not None:
        embed = discord.Embed(
            title=f'Message de {message.author.name} dans #{message.channel.name}',
            description=f'{message.content} dans #{message.channel.name}',
            color=discord.Color.teal(),
            timestamp=datetime.now()
        )
@bot.event
async def on_message_delete(message):
    LOG_MESSAGE = 1301093052206551061
    log_channel = bot.get_channel(LOG_MESSAGE)
    
    if log_channel is not None:
        embed = discord.Embed(
            title=f'Message supprimé de {message.author.name} dans {message.channel.mention}',
            description=f'{message.content} envoyé dans #{message.channel.name}',
            color=0x478487,
            timestamp=datetime.now()
        )
        
        await log_channel.send(embed=embed)
    else:
        print(f"Erreur : Le salon de logs avec l'ID {LOG_MESSAGE} n'a pas été trouvé.")
        

def create_small_embed(description=None, color=0xA89494):
	embed = discord.Embed(
		description=description,
		color=color
	)
	return embed
@bot.event
async def on_member_remove(member):
    LOG_JOINLEAVE = 1301094484058046524
    log_channel = bot.get_channel(LOG_JOINLEAVE)
    server = bot.guilds[0]
    member_count = server.member_count
    await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name=f"the server"))
    embed = discord.Embed(
        title=f"{member.name} a quitté le serveur. {get_emoji('Offline')}",
        color=0xd65617,
        timestamp=datetime.now()
    )
    
    await log_channel.send(embed=embed)

join_times = load_data("state_raid.json")
guild=discord.guild


@bot.event
async def on_member_join(member):
    if anti_join_active:
        try:
            await member.kick(reason="Anti-join activé : Les nouveaux membres sont bloqués.")
            log_channel = member.guild.get_channel(1306346010917867591)
            if log_channel:
                await log_channel.send(f"🚨 {member.mention} a été expulsé automatiquement en raison de l'anti-join.")
        except Exception as e:
            print(f"Erreur lors de l'expulsion de {member.name}: {e}")
    guild_id = str(member.guild.id)
    current_time = datetime.utcnow()

    if anti_join_enabled.get(guild_id, False):
        log_channel = member.guild.get_channel(1306346010917867591)
        if log_channel:
            await log_channel.send(f"❌ {member.mention} a tenté de rejoindre, mais les adhésions sont désactivées.")
        return

    if guild_id not in join_times:
        join_times[guild_id] = []
    
    join_times[guild_id] = [
    time for time in join_times[guild_id]
    if isinstance(time, str) and time != "enabled" and current_time - datetime.fromisoformat(time) < timedelta(minutes=2)
]

    join_times[guild_id].append(current_time.isoformat())

    save_data_raid(join_times)

    if len(join_times[guild_id]) > 5:
        await trigger_raid_protection(member.guild, "Afflux massif de nouvelles adhésions.")
        log_channel = member.guild.get_channel(1306346010917867591)
        if log_channel:
            await log_channel.send("🚨 Anti-Raid activé automatiquement.")

    welcome_channel = bot.get_channel(1272526126526369812)
    if welcome_channel is None:
        print("Erreur : Salon de bienvenue introuvable.")
        return
    embed = discord.Embed(
        title=f"Bienvenue sur le serveur {member.display_name} !!!",
        description=f"Amuse-toi bien sur ce serveur {member.mention} 🎉",
        color=0xDD33FF
    )
    
    file = discord.File("banniere_join.png", filename="banniere_join.png")
    embed.set_image(url="attachment://banniere_join.png")
    
    await welcome_channel.send(embed=embed, file=file)
    LOG_JOINLEAVE = 1301094484058046524
    log_channel = bot.get_channel(LOG_JOINLEAVE)
    await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name=f"the server"))
    embed = discord.Embed(
        title=f"{member.name} a rejoint le serveur. {get_emoji('Online')}",
        color=0x1616a7,
        timestamp=datetime.now()
    )

    await log_channel.send(embed=embed)
    role = member.guild.get_role(1272530966283554826)
    if role:
        await member.add_roles(role)

def create_embed(title=None, description=None, color=discord.Color.gold()):
	embed = discord.Embed(
		title=title,
		description=description,
		color=color
	)
	embed.timestamp = datetime.utcnow()
	embed.set_footer(text='', icon_url='') 
	return embed

@bot.event
async def on_app_command(interaction):
    LOG_COMMAND = 1301098651678019584
    log_channel = bot.get_channel(LOG_COMMAND)
    embed = discord.Embed(
        title=f'Commande exécutée par {interaction.author.name}',
        description=interaction.message.content,
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    await log_channel.send(embed=embed)
    

if SERVER:
    run_bot()
else:
    bot.run(TOTO)
