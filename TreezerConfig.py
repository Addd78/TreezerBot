import asyncio
import os
import json
from discord.ext import tasks
import discord
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
    check_temporary_roles.start()
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
                  ################# STATS ######################

"""TIKTOK_USERNAME = "ilian_amd"
TWITCH_CLIENT_ID = "your_twitch_client_id"
TWITCH_CLIENT_SECRET = "your_twitch_client_secret"
TWITCH_USER_ID = "twitch_channel_user_id"

STATS_FILE = "stats.json"
api = TikTokApi()

def load_stats():
    if not os.path.exists(STATS_FILE):
        with open(STATS_FILE, "w") as file:
            json.dump({"tiktok_channel_id": None, "twitch_channel_id": None}, file)
    with open(STATS_FILE, "r") as file:
        return json.load(file)

def save_stats(data):
    with open(STATS_FILE, "w") as file:
        json.dump(data, file)

stats = load_stats()

try:
    api = TikTokApi.get_instance(custom_verify_fp="your_verify_fp", use_test_endpoints=True)
except Exception as e:
    print(f"Erreur lors de l'initialisation de l'API TikTok : {e}")

async def get_tiktok_follower_count():
    try:
        user_info = api.user(username=TIKTOK_USERNAME).info()
        follower_count = user_info["stats"]["followerCount"]
        return follower_count
    except Exception as e:
        print(f"Erreur lors de la récupération du nombre d'abonnés TikTok : {e}")
        return None
def get_twitch_access_token():
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    response = requests.post(url, params=params)
    return response.json().get("access_token")

def get_twitch_follower_count():
    access_token = get_twitch_access_token()
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }
    url = f"https://api.twitch.tv/helix/users/follows?to_id={TWITCH_USER_ID}"
    response = requests.get(url, headers=headers)
    data = response.json()
    return data["total"] if "total" in data else 0

@bot.tree.command(name="creer_salon_abonnes", description="Crée un salon vocal pour afficher les abonnés TikTok et Twitch.")
@discord.app_commands.checks.has_permissions(administrator=True)
async def creer_salon_abonnes(interaction: discord.Interaction):
    guild = interaction.guild

    tiktok_follower_count = await get_tiktok_follower_count()
    tiktok_channel_name = f"Abonnés TikTok : {tiktok_follower_count}"
    tiktok_channel = await guild.create_voice_channel(name=tiktok_channel_name, category=guild.get_channel(1276554503700742307))
    stats["tiktok_channel_id"] = tiktok_channel.id

    twitch_follower_count = get_twitch_follower_count()
    twitch_channel_name = f"Abonnés Twitch : {twitch_follower_count}"
    twitch_channel = await guild.create_voice_channel(name=twitch_channel_name, category=guild.get_channel(1276554503700742307))
    stats["twitch_channel_id"] = twitch_channel.id

    save_stats(stats)
    await interaction.response.send_message("Salons vocaux créés pour suivre les abonnés TikTok et Twitch.", ephemeral=True)

@tasks.loop(minutes=10)
async def update_follower_channels():
    guild = bot.get_guild(DISCORD_GUILD_ID)

    tiktok_channel = guild.get_channel(stats["tiktok_channel_id"])
    tiktok_follower_count = await get_tiktok_follower_count()
    if tiktok_channel and tiktok_follower_count is not None:
        await tiktok_channel.edit(name=f"Abonnés TikTok : {tiktok_follower_count}")

    twitch_channel = guild.get_channel(stats["twitch_channel_id"])
    twitch_follower_count = get_twitch_follower_count()
    if twitch_channel and twitch_follower_count is not None:
        await twitch_channel.edit(name=f"Abonnés Twitch : {twitch_follower_count}")"""

    
                  ################ ECONOMIE ####################
ECONOMY_FILE = "economie.json"
def load_data():
    if os.path.exists(ECONOMY_FILE):
        with open(ECONOMY_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_data(data):
    with open(ECONOMY_FILE, 'w') as file:
        json.dump(data, file, indent=4)

economy_data = load_data()

roles = {
    1: 1298591387469484073,
    10: 1298591387477999668,
    25: 1298591388279242823,
    50: 1298591389164113983,
    75: 1298592077713768448,
    100: 1298592254184656896,
}
shop_items = {
    "3000": {"price": 3000, "xp": 550},
    "15000": {"price": 15000, "xp": 1000},
    "35000": {"price": 35000, "role_id": 1301225106990694455},
    "80000": {"price": 80000, "ticket_category_id": 1299809436550041673},
    "100000": {"price": 100000, "role_id": 1300097097814507542, "duration": 604800}
}
user_messages = {}
@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author.bot:
        return

    user_id = message.author.id
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
    if message.author.bot:
        return

    user_id = str(message.author.id)
    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 0})
    user_data["coins"] += 75
    economy_data[user_id] = user_data
    save_data(economy_data)

    await bot.process_commands(message)

async def update_level(member, user_data, interaction: discord.Interaction):
    xp_needed = 1000 * user_data["level"]

    if user_data["xp"] >= xp_needed:
        user_data["level"] += 1
        user_data["xp"] -= xp_needed
        new_level = user_data["level"]

        embed = discord.Embed(
            title=f"{get_emoji('redwings')}Rankup",
            description=f"Félicitations à {member.mention} ! Vous avez atteint le niveau {new_level} !",
            color=0x131fd1
        )

        file = discord.File("update_level_banner.png", filename="update_level_banner.png")
        embed.set_image(url="attachment://update_level_banner.png")

        if new_level in roles:
            role = member.guild.get_role(roles[new_level])
            if role:
                await member.add_roles(role)

        channel_lvl = interaction.guild.get_channel(1302369087095046184)
        if channel_lvl:
            await channel_lvl.send(embed=embed, file=file)

        save_data(economy_data)

    
@bot.tree.command(name="rankup", description="Améliorez votre niveau si vous avez assez d'XP.")
async def rankup(interaction):
    user_id = str(interaction.user.id)
    economy_data = load_data()
    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 1})
    if user_data["xp"] >= 1000:
        await update_level(interaction.user, user_data, interaction)
        economy_data[user_id] = user_data
        save_data(economy_data)
        embed = create_small_embed("Vous avez amélioré votre niveau avec succès !")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = create_small_embed("Vous n'avez pas assez d'XP pour passer au niveau suivant.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShopSelect())

class ShopSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="550 XP", description="3000 TreezCoins", value="3000"),
            discord.SelectOption(label="1000 XP", description="15000 TreezCoins", value="15000"),
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
                embedachat=create_small_embed(f"Vous avez acheté {item['xp']} XP pour {item['price']} TreezCoins. {get_emoji('yes')}")
                await interaction.user.send(embed=embedachat)
                await interaction.response.send_message(embed=embedachat, ephemeral=True)
            elif "role_id" in item:
                role = interaction.guild.get_role(item["role_id"])
                if role:
                    embedachat= create_small_embed(f"Vous avez acheté le rôle pour {item['price']} TreezCoins. {get_emoji('yes')}")
                    await interaction.user.add_roles(role)
                    await interaction.user.send(embed=embedachat)
                    await interaction.response.send_message(embed=embedachat, ephemeral=True)
            elif "ticket_category_id" in item:
                category = interaction.guild.get_channel(item["ticket_category_id"])
                if category:
                    overwrites = {
    interaction.guild.default_role: PermissionOverwrite(read_messages=False),
    interaction.user: PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
    interaction.guild.me: PermissionOverwrite(read_messages=True, send_messages=True)
}
                    
                    await category.create_text_channel(f"ticket-{interaction.user.display_name}", overwrites = overwrites)
                    await interaction.response.send_message("Vous avez ouvert un ticket d'événement.", ephemeral=True)

            economy_data[user_id] = user_data
            save_data(economy_data)
            await update_level(interaction.user, user_data, interaction)
        else:
            await interaction.response.send_message(f"Vous n'avez pas assez de TreezCoins pour cet item. {get_emoji('no')}", ephemeral=True)
    async def add_temporary_role(user, role_id, duration_days=7):
        user_id = str(user.id)
        expiration_date = datetime.utcnow() + timedelta(days=duration_days)
        if "temporary_roles" not in economy_data:
            economy_data["temporary_roles"] = {}
        economy_data["temporary_roles"][user_id] = {
            "role_id": role_id,
            "expiration_date": expiration_date.isoformat()}
        save_data(economy_data)
        role = user.guild.get_role(role_id)
        await user.add_roles(role)

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

@bot.tree.command(name="treezcoins", description="Affiche vos informations TreezCoins.")
async def treezCoins(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_data = economy_data.get(user_id, {"coins": 0, "xp": 0, "level": 1})
    embed = discord.Embed(title="Vos informations TreezCoins", color=0x00ff00)
    embed.add_field(name="TreezCoins", value=f"{user_data['coins']} coins", inline=False)
    embed.add_field(name="XP", value=f"{user_data['xp']} XP", inline=False)
    embed.add_field(name="Niveau", value=f"Niveau {user_data['level']}", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)    

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
        title=f"Bienvenue sur le serveur {member.mention} !!!",
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