import asyncio
import os
import json
import random
import aiohttp
from discord.ext import tasks
import discord
from TikTokApi import TikTokApi
from math import floor
import traceback
from discord.utils import get
from discord.ui import View, Select
from discord.ext import commands
from discord import VoiceChannel, Embed, PermissionOverwrite
from datetime import datetime, timezone, timedelta

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
        views = [RemoteButtonView(), ShopView()]
        for element in views:
            self.add_view(element)
        
bot = PersistentViewBot()

@bot.command()
async def sync(ctx):
    synced = await ctx.bot.tree.sync()
    await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name=f"the server"))
    await ctx.send(f"Synced {len(synced)} commands")

tree = bot.tree

def run_bot(token=TOTO, debug=False):
    if debug: print(bot._connection.loop)
    bot.run(token)
    if debug: print(bot._connection.loop)
    return bot._connection.loop.is_closed()

@bot.event
async def on_ready():
    check_for_free_games.start() 
    award_treezcoins_for_vc.start()
    check_temporary_roles.start()
    bot.loop.create_task(start_drops())
    print(f'Connecté en tant que {bot.user}!')

def load_emojis(filename='emojis.json'):
    with open(filename, 'r') as file:
        return json.load(file)

emojis = load_emojis()

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

        
#################################### TICKETS  #############################################


@bot.tree.command(name="send_remote_button")
@discord.app_commands.checks.has_permissions(administrator=True)
async def send_remote_button(interaction: discord.Interaction):
    """Envoyer l'embed des ticket + Bouton"""
    staff_role = interaction.guild.get_role(1292930841286021210)
    if staff_role not in interaction.user.roles:
        embed = create_small_embed(f"Vous n'avez pas la permission d'utiliser cette commande {get_emoji('no')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

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

        ticket_data_ = {
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
########### JEUX GRATUITS ##############

FREE_GAMES_CHANNEL_ID = 1304515694620180542
CHECK_INTERVAL = 3600
detected_games = set()

async def fetch_free_games():
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                games = []
                for game in data['data']['Catalog']['searchStore']['elements']:
                    if game['promotions']:
                        for promotion in game['promotions']['promotionalOffers']:
                            if promotion['promotionalOffers']:
                                games.append({
                                    "title": game['title'],
                                    "description": game['description'],
                                    "thumbnail": game['keyImages'][0]['url'],
                                    "url": f"https://www.epicgames.com/store/fr/p/{game['productSlug']}"
                                })
                return games
            else:
                print(f"Erreur lors de la requête API : {response.status}")
                return []

async def check_new_free_games():
    free_games = await fetch_free_games()
    channel = bot.get_channel(FREE_GAMES_CHANNEL_ID)
    
    for game in free_games:
        game_id = game["title"]
        if game_id not in detected_games:
            detected_games.add(game_id)
            
            embed = discord.Embed(
                title=game["title"],
                description=game["description"],
                color=discord.Color.blue()
            )
            embed.set_image(url=game["thumbnail"])
            embed.add_field(name="Lien", value=f"[Voir sur Epic Games Store]({game['url']})", inline=False)
            
            await channel.send(embed=embed)

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_for_free_games():
    await check_new_free_games()

################ VOC #################

TREEZCOINS_REWARD = 35
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

        with open(ECONOMY_FILE, 'r') as f:
            economie = json.load(f)

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
        await asyncio.sleep(random.randint(7200, 84600))
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





ECONOMY_FILE = "economie.json"
roles = {
    1: 1298591387469484073,
    10: 1298591387477999668,
    25: 1298591388279242823,
    50: 1298591389164113983,
    75: 1298592077713768448,
    100: 1298592254184656896,
}
shop_items = {
    "5000": {"price": 5000, "xp": 550},
    "11000": {"price": 11000, "xp": 1150},
    "35000": {"price": 35000, "role_id": 1301225106990694455},
    "80000": {"price": 80000, "ticket_category_id": 1299809436550041673},
    "100000": {"price": 100000, "role_id": 1300097097814507542, "duration": 604800}
}
user_messages = {}
log_channel_id = 1302716998983221298
rankup_channel_id = 1302369087095046184

def load_data():
    if os.path.exists(ECONOMY_FILE):
        with open(ECONOMY_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_data(data):
    with open(ECONOMY_FILE, 'w') as file:
        json.dump(data, file, indent=4)

economy_data = load_data()

@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author.bot:
        return

    user_id = str(message.author.id)
    now = datetime.utcnow()

    user_messages[user_id] = [msg_time for msg_time in user_messages.get(user_id, []) if now - msg_time < timedelta(minutes=1)]
    user_messages[user_id].append(now)

    if len(user_messages[user_id]) >= 10:
        try:
            await message.author.timeout(timedelta(seconds=60), reason="Spam détecté")
        except discord.Forbidden:
            pass
        log_channel = bot.get_channel(1301664792586752051)
        embed = discord.Embed(title="Action anti-spam", color=discord.Color.red())
        embed.add_field(name="Membre", value=message.author.mention, inline=True)
        embed.add_field(name="Raison", value="Spam détecté (10 messages en moins d'une minute)", inline=False)
        embed.add_field(name="Action", value="Timeout de 60 secondes", inline=False)
        await log_channel.send(embed=embed)
        user_messages[user_id] = []

    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 1})
    user_data["coins"] += 75
    economy_data[user_id] = user_data
    await update_level(message.author, user_data)
    save_data(economy_data)

async def update_level(member, user_data):
    xp_needed = 1000
    while user_data["xp"] >= xp_needed:
        user_data["level"] += 1
        user_data["xp"] -= xp_needed
        xp_needed = 1000 * user_data["level"]
        
        embed = discord.Embed(
            title=f"🎉 Rankup",
            description=f"Félicitations à {member.mention} ! Vous avez atteint le niveau {user_data['level']} !",
            color=0x131fd1
        )
        file = discord.File("update_level_banner.png", filename="update_level_banner.png")
        embed.set_image(url="attachment://update_level_banner.png")

        if user_data["level"] in roles:
            role = member.guild.get_role(roles[user_data["level"]])
            if role and role not in member.roles:
                await member.add_roles(role)

        rankup_channel = member.guild.get_channel(rankup_channel_id)
        if rankup_channel:
            await rankup_channel.send(embed=embed, file=file)

        log_channel = member.guild.get_channel(log_channel_id)
        if log_channel:
            log_embed = discord.Embed(
                title="Nouveau Rankup",
                description=f"{member.mention} est passé au niveau {user_data['level']}.",
                color=discord.Color.green()
            )
            await log_channel.send(embed=log_embed)

    
@bot.tree.command(name="rankup", description="Améliorez votre niveau si vous avez assez d'XP.")
async def rankup(interaction):
    user_id = str(interaction.user.id)
    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 1})
    if user_data["xp"] >= 1000:
        await update_level(interaction.user, user_data)
        economy_data[user_id] = user_data
        save_data(economy_data)
        embed = discord.Embed(description="Vous avez amélioré votre niveau avec succès !", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(description="Vous n'avez pas assez d'XP pour passer au niveau suivant.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShopSelect())

class ShopSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="550 XP", description="5000 TreezCoins", value="5000"),
            discord.SelectOption(label="1150 XP", description="11000 TreezCoins", value="11000"),
            discord.SelectOption(label="Pass Concept", description="35000 TreezCoins", value="35000"),
            discord.SelectOption(label="Choix d'évènement", description="80000 TreezCoins", value="80000"),
            discord.SelectOption(label="PASS VIP (1 semaine)", description="100000 TreezCoins", value="100000")
        ]
        super().__init__(placeholder="Choisissez une option...", min_values=1, max_values=1, options=options, custom_id="shop_select")

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 1})
        choice = self.values[0]
        item = shop_items[choice]

        if user_data["coins"] >= item["price"]:
            user_data["coins"] -= item["price"]
            if "xp" in item:
                user_data["xp"] += item["xp"]
                await update_level(interaction.user, user_data)
                embedachat = discord.Embed(description=f"Vous avez acheté {item['xp']} XP pour {item['price']} TreezCoins.", color=discord.Color.green())
                await interaction.response.send_message(embed=embedachat, ephemeral=True)
            elif "role_id" in item:
                role = interaction.guild.get_role(item["role_id"])
                if role:
                    await interaction.user.add_roles(role)
                    embedachat = discord.Embed(description=f"Vous avez acheté un rôle pour {item['price']} TreezCoins.", color=discord.Color.green())
                    await interaction.response.send_message(embed=embedachat, ephemeral=True)
            elif "ticket_category_id" in item:
                category = interaction.guild.get_channel(item["ticket_category_id"])
                if category:
                    overwrites = {
                        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
                        interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    }
                    await category.create_text_channel(f"ticket-{interaction.user.display_name}", overwrites=overwrites)
                    await interaction.response.send_message("Vous avez ouvert un ticket d'événement.", ephemeral=True)

            economy_data[user_id] = user_data
            save_data(economy_data)
        else:
            embedachat = discord.Embed(description="Vous n'avez pas assez de TreezCoins pour cet item.", color=discord.Color.red())
            await interaction.response.send_message(embed=embedachat, ephemeral=True)

@bot.tree.command(name="treezcoins", description="Affiche vos informations TreezCoins.")
async def treezcoins(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    try:
        with open('economie.json', 'r') as f:
            economy_data = json.load(f)
    except FileNotFoundError:
        economy_data = {}

    if user_id in economy_data:
        user_data = economy_data[user_id]
    else:
        user_data = {"coins": 0, "xp": 0, "level": 0}

    embed = discord.Embed(title="Vos informations TreezCoins", color=0x00ff00)
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
    save_data(economy_data)
    
@bot.tree.command()
@discord.app_commands.checks.has_permissions(administrator=True)
async def shop(interaction):
    embed = discord.Embed(title="TreezCoins Shop", description="Choisissez une option pour acheter des récompenses avec vos TreezCoins !", color=0x00ff00)
    await interaction.response.send_message(embed=embed, view=ShopView()) 
    
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

@bot.tree.command(name="addcoins", description="Ajouter des TreezCoins à un membre.")
@discord.app_commands.checks.has_permissions(administrator=True)
async def addcoins(interaction: discord.Interaction, member: discord.Member, quantité: int):
    if quantité <= 0:
        await interaction.response.send_message("La quantité de TreezCoins doit être positive.", ephemeral=True)
        return

    user_id = str(member.id)
    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 1})
    user_data["coins"] += quantité
    economy_data[user_id] = user_data
    save_data(economy_data)

    log_channel = bot.get_channel(log_channel_coins_id)
    embed_log = discord.Embed(
        title="Ajout de TreezCoins",
        description=f"{interaction.user.mention} a ajouté {quantité} TreezCoins à {member.mention}.",
        color=discord.Color.blue()
    )
    await log_channel.send(embed=embed_log)

    await interaction.response.send_message(f"{quantité} TreezCoins ajoutés à {member.mention}.", ephemeral=True)

@bot.tree.command(name="addxp", description="Ajouter de l'XP à un membre.")
async def addxp(interaction: discord.Interaction, member: discord.Member, quantité: int):
    if quantité <= 0:
        await interaction.response.send_message("La quantité d'XP doit être positive.", ephemeral=True)
        return

    user_id = str(member.id)
    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 1})
    initial_xp = user_data["xp"]
    initial_level = user_data["level"]

    user_data["xp"] += quantité

    xp_total = user_data["xp"]
    levels_gained = floor(xp_total / 1000)
    remaining_xp = xp_total % 1000

    user_data["level"] += levels_gained
    user_data["xp"] = remaining_xp

    economy_data[user_id] = user_data
    save_data(economy_data)

    rankup_channel = bot.get_channel(rankup_channel_id)
    for level in range(initial_level + 1, user_data["level"] + 1):
        embed_rankup = discord.Embed(
            title=f"🎉 Rankup",
            description=f"Félicitations à {member.mention} ! Vous avez atteint le niveau {level} !",
            color=0x131fd1
        )
        file = discord.File("update_level_banner.png", filename="update_level_banner.png")
        embed_rankup.set_image(url="attachment://update_level_banner.png")
        await rankup_channel.send(embed=embed_rankup, file=file)

    log_channel = bot.get_channel(log_channel_xp_id)
    embed_log = discord.Embed(
        title="Ajout d'XP",
        description=(
            f"{interaction.user.mention} a ajouté {quantité} XP à {member.mention}.\n"
            f"XP initial: {initial_xp}\n"
            f"XP actuel: {user_data['xp']}\n"
            f"Level initial: {initial_level}\n"
            f"Level actuel: {user_data['level']}"
        ),
        color=discord.Color.green()
    )
    await log_channel.send(embed=embed_log)

    await interaction.response.send_message(
        f"{quantité} XP ajoutés à {member.mention}. {levels_gained} niveaux gagnés." if levels_gained > 0 else f"{quantité} XP ajoutés à {member.mention}.",
        ephemeral=True
    )
    
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

@bot.event
async def on_member_join(member):
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