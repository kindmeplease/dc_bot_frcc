import keep_alive
import discord
from discord.ext import commands
import os
my_secret = os.getenv['DISCORD_TOKEN']

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
# 設定機器人前綴
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')#不重要

@bot.event
async def on_message(message):
    # 確保機器人不會回覆自己
    if message.author == bot.user:
        return
    # 檢查消息中是否提到了機器人
    if bot.user in message.mentions:
        await message.channel.send(f'Hello {message.author.mention}, how can I help you?')
    # 確保命令仍然可以正常工作
    await bot.process_commands(message)

@bot.event#身分組
async def on_raw_reaction_add(payload):
    # 濾除機器人反應
    if payload.member.bot:
        return

    # 獲取頻道和消息對象
    channel = bot.get_channel(payload.channel_id)
    message_id = 1289597020578906142  # 替換為您的特定消息 

    # 檢查頻道名稱和消息 ID
    if channel.name == "一般" and payload.message_id == message_id:
        if str(payload.emoji) == "💛":
            role = discord.utils.get(payload.member.guild.roles, name="1")
            if role is not None:
                await payload.member.add_roles(role)
                await payload.member.send(f"已將身分組 {role.name} 授予給你.")
@bot.event
async def on_member_join(member):
    print("Member joined:", member)  # Add this line to check if the event is triggered
    print("Bot is ready:", bot.is_ready())  # Check if the bot is ready
    print("Intents:", bot.intents)  # Check the enabled intents
    print("Channel ID:", 1050713364923416649)  # Check the channel ID
    channel = bot.get_channel(1050713364923416649)
    if channel:
        print("Channel found:", channel)  # Check if the channel is found
        try:
            await channel.send(f"歡迎 {member.mention}！這是固定訊息。")  # @提及新人
            print("Welcome message sent!")  # Check if the message was sent
        except discord.Forbidden:
            print("Forbidden to send message!")  # Check for permission errors
        except discord.HTTPException as e:
            print("HTTP Exception:", e)  # Check for HTTP errors
    else:
        print("Channel not found!")  # Check if the channel is not found

@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')
# 用您的令牌啟動機器人
keep_alive.keep_alive()
bot.run(my_secret)
