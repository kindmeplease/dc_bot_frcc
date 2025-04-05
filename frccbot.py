import keep_alive
import discord
from discord.ext import commands
import os
import aiohttp
from datetime import datetime
my_secret = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ESI API settings
ESI_BASE_URL = "https://esi.evetech.net/latest"
JITA_REGION_ID = 10000002  # The Forge region (Jita)
JITA_SYSTEM_ID = 30000142  # Jita 4-4
PERIMETER_SYSTEM_ID = 30000144  # Perimeter system
USER_AGENT = "ItemMarketBot/1.0 (contact: wuc965726@gmail.com)"
global real_item
real_item=True
global over_five
over_five=False
async def fetch_item_type_id(item_name, delay=1):
    """Fetch the type_id of an item by its name using /universe/ids/ endpoint."""
    async with aiohttp.ClientSession() as session:
        url = f"{ESI_BASE_URL}/universe/ids/?datasource=tranquility"
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json"
        }
        name = item_name.lower()
        payload = [name]
        
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    print(f"Failed to fetch type_id for '{name}'. Status: {response.status}")
                    return None, None
                data = await response.json()
                if 'inventory_types' not in data or not data['inventory_types']:
                    print(f"No inventory types found for '{name}'.")
                    return None, None
                type_id = data['inventory_types'][0]['id']
                actual_name = data['inventory_types'][0]['name']
                return type_id, actual_name
        except aiohttp.ClientError as e:
            print(f"Error fetching type_id for '{name}': {e}")
            return None, None

async def fetch_market_data(type_id, region_id):
    """Fetch market data for a given type_id in a region."""
    global real_item
    async with aiohttp.ClientSession() as session:
        url = f"{ESI_BASE_URL}/markets/{region_id}/orders/?datasource=tranquility&type_id={type_id}"
        headers = {"User-Agent": USER_AGENT}
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                real_item=False
                print(f"Failed to fetch market data for type_id {type_id} in region {region_id} - Status: {response.status}")
                return None
            data = await response.json()
            return data

def calculate_top_5_percent_avg(orders):
    """Calculate the average price of the top 5% of item volume, excluding extreme values."""
    global over_five
    if not orders:
        return 0
    
    if orders[0]['is_buy_order']:
        sorted_orders = sorted(orders, key=lambda x: x['price'], reverse=True)
    else:
        sorted_orders = sorted(orders, key=lambda x: x['price'], reverse=False)
    
    # Use the first sorted price as reference (highest for buy, lowest for sell)
    reference_price = sorted_orders[0]['price']
    threshold = reference_price / 2  # Define extreme value as less than half of reference
    
    total_volume = sum(order['volume_remain'] for order in sorted_orders if order['price'] >= reference_price / 2 and order['price']<=reference_price*2)
    if total_volume == 0:
        return 0
    target_volume = total_volume * 0.05
    
    accumulated_volume = 0
    weighted_price_sum = 0
    
    for order in sorted_orders:
        volume = order['volume_remain']
        price = order['price']
        
        # Skip extreme values
        if price < threshold:
            over_five=True
            continue
        
        if accumulated_volume + volume > target_volume:
            remaining_volume = target_volume - accumulated_volume
            weighted_price_sum += remaining_volume * price
            accumulated_volume = target_volume
            break
        else:
            weighted_price_sum += volume * price
            accumulated_volume += volume
        
    if accumulated_volume == 0:
        return 0
    return weighted_price_sum / accumulated_volume

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    global over_five
    if message.author == bot.user:
        return
    if bot.user in message.mentions:
        await message.channel.send(f'Hello {message.author.mention}, how can I help you?')
    
    if message.content.startswith('!'):
        item_name = message.content[1:].strip()

        if not item_name:
            await message.channel.send("請提供物品名稱，例如 `!Gila` 或 `!Tritanium`")
            return

        type_id, actual_name = await fetch_item_type_id(item_name)
        
        if not type_id:
            await message.channel.send(f"找不到物品 '{item_name}'，請確認名稱是否正確（需使用英文名稱）！\n如果問題持續，請聯繫管理員檢查 API 狀態。")
            return

        market_data = await fetch_market_data(type_id, region_id=JITA_REGION_ID)
        
        if not market_data and real_item==False:
            await message.channel.send(f"無法獲取 {actual_name} 的市場數據，請稍後再試！")
            return

        buy_orders = [order for order in market_data if order['is_buy_order'] and order['system_id'] in [JITA_SYSTEM_ID, PERIMETER_SYSTEM_ID]]
        sell_orders = [order for order in market_data if not order['is_buy_order']]

        highest_buy = max([order['price'] for order in buy_orders], default=0)
        lowest_sell = min([order['price'] for order in sell_orders], default=0)
        
        buy_5_percent_avg = calculate_top_5_percent_avg(buy_orders)
        sell_5_percent_avg = calculate_top_5_percent_avg(sell_orders)

        embed = discord.Embed(
            title=f"{actual_name} 市場資訊 (Jita & Perimeter)",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="最高買單價格 (Jita+Perimeter)", value=f"{highest_buy:,.2f} ISK", inline=True)
        embed.add_field(name="最低賣單價格 (Jita)", value=f"{lowest_sell:,.2f} ISK", inline=True)
        embed.add_field(name="均價(去除極端值) (Jita+Perimeter)" if over_five else "買單前 5% 均價 (Jita+Perimeter)" , value=f"{buy_5_percent_avg:,.2f} ISK", inline=True)
        embed.add_field(name="賣單前 5% 均價 (Jita)", value=f"{sell_5_percent_avg:,.2f} ISK", inline=True)
        embed.set_footer(text="數據來源：ESI API")
        over_five=False
        await message.channel.send(embed=embed)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.member.bot:
        return
    channel = bot.get_channel(payload.channel_id)
    message_id = 1289597020578906142
    if channel.name == "一般" and payload.message_id == message_id:
        if str(payload.emoji) == "💛":
            role = discord.utils.get(payload.member.guild.roles, name="1")
            if role is not None:
                await payload.member.add_roles(role)
                await payload.member.send(f"已將身分組 {role.name} 授予給你.")

@bot.event
async def on_member_join(member):
    print("Member joined:", member)
    print("Bot is ready:", bot.is_ready())
    print("Intents:", bot.intents)
    print("Channel ID:", 1050713364923416649)
    channel = bot.get_channel(1050713364923416649)
    if channel:
        print("Channel found:", channel)
        try:
            await channel.send(f"歡迎 {member.mention}！這是固定訊息。")
            print("Welcome message sent!")
        except discord.Forbidden:
            print("Forbidden to send message!")
        except discord.HTTPException as e:
            print("HTTP Exception:", e)
    else:
        print("Channel not found!")

@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')

#keep_alive.keep_alive()
bot.run(my_secret))
