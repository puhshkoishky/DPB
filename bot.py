#TODO: 
#DELETE embed from shorts links it processes, 
#detect if video filesize will be larger than 25MB


#abstracts api for Ollama and openrouter use case
from api1 import API1
from api2 import API2

import requests
import json
import subprocess
import glob
import os
import discord
from dotenv import load_dotenv
from pytube import YouTube
from discord.ext import commands

#the following is the api logic for swtiching between two apis


# 1. Bot Context Class (handles the bot's interaction with the API)
class BotContext:
    def __init__(self, api):
        self.api = api

    def fetch_data(self):
        return self.api.fetch_data()

    def send_data(self, data):
        return self.api.send_data(data)

# 2. API Switching Logic
def switch_api(api_name: str):
    """Switch between API implementations based on the config or input"""
    if api_name == "API1":
        return API1()
    elif api_name == "API2":
        return API2()
    else:
        raise ValueError(f"API '{api_name}' not supported.")

# 3. Optional: Load Configuration from JSON (or Environment Variable)
def load_configuration():
    """Simulate loading configuration to decide which API to use"""
    try:
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
            return config.get('api_choice', 'API1')  # Default to API1 if not set
    except FileNotFoundError:
        print("Configuration file not found. Defaulting to API1.")
        return "API1"  # Default to API1 if config file is not found


# Load environment variables from .env file
load_dotenv()

# Get API keys and tokens from environment variables
api_key = os.getenv("OPENROUTER_API_KEY")
discord_token = os.getenv("DISCORD_TOKEN")

# URL for OpenRouter API
url = "https://openrouter.ai/api/v1/chat/completions"

# Set authorization headers
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Event: When the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# Command: Responds with "Pong!" when the user types "!ping"
@bot.command()
async def ping(ctx):
    await ctx.send("pong!")
    
# Command: Saves the user's thoughts into thoughts.txt
@bot.command()
async def thoughts(ctx, *, thought: str):
    with open("thoughts.txt", "a") as file:
        file.write(f"user {ctx.author}: {thought}\n")
    await ctx.send(f"Your thought has been saved, {ctx.author}!")

# Command: Summarizes the thoughts of a specific user using LLM
@bot.command()
async def opinions(ctx, *, username: str):
    user_thoughts = []
    with open("thoughts.txt", "r") as file:
        for line in file:
            if f"user {username}:" in line:
                user_thoughts.append(line.strip())

    if not user_thoughts:
        await ctx.send(f"No thoughts found for {username}.")
        return

    thoughts_text = "\n".join(user_thoughts)
    prompt = f"For user {username}, summarize their opinions in 20 words or less: {thoughts_text}"
    data = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        summary = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        with open("LLMthoughts.txt", "a") as summary_file:
            summary_file.write(f"Summary for {username}:\n{summary}\n\n")
        await ctx.send(f"Summary of {username}'s thoughts:\n{summary}")
    else:
        await ctx.send("Sorry, there was an error summarizing the thoughts.")

# Event: Listen for messages containing certain text
@bot.event
async def on_message(message):
    # Ignore the bot's own messages
    if message.author == bot.user:
        return

    # Check if the message contains the word "shorts"
    if 'shorts' in message.content:
        await message.channel.send(f"Hi {message.author.mention}, Morgi doesn't like 'shorts'!")

        # Check if the message contains an embed (e.g., YouTube Shorts links)
        for embed in message.embeds:
            if embed.url.startswith("https://discordapp.com/channels/"):
                embed.url = None
                await message.edit(embed=embed)

        # Download YouTube Shorts video
        directory = '/root/ytshortsbot/FileCache/'
        shortURL = message.content
        os.chdir(directory)

        # Run yt-dlp to download the video
        result = subprocess.run(['/root/ytshortsbot/venv/bin/yt-dlp', shortURL], capture_output=True, text=True)
        if result.returncode == 0:
            vidFiles = glob.glob(os.path.join(directory, "*"))

            # Check if the downloaded file is over 25MB
            file_size = os.path.getsize(vidFiles[0]) if vidFiles else 0
            if file_size > 8 * 1024 * 1024:
                await message.channel.send("The video is too large to be sent over Discord (over 25MB).")
            else:
                await message.channel.send(file=discord.File(vidFiles[0]))

            # Delete the file after sending
            if os.path.exists(vidFiles[0]):
                os.remove(vidFiles[0])
        else:
            await message.channel.send("Error downloading the video.")

    # Ensure commands still work
    await bot.process_commands(message)

# Run the bot with the token from the .env file
bot.run(discord_token)

