import os
import subprocess
import glob
import discord
from discord.ext import commands
from dotenv import load_dotenv
from pytube import YouTube
import ollama
import re

# Load environment variables from .env file
load_dotenv()

# Get API keys and tokens from environment variables
discord_token = os.getenv("DISCORD_TOKEN")

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Directory for downloading videos
directory = '/root/ytshortsbot/FileCache/'

# Perform Review function using Ollama (interface similar to PerformReview)
def PerformReview(text, model="deepseek-r1:7b", max_length=300):
    """
    Generate a performance review using Ollama's LLM.
    """
    try:
        # Ensure text is within the model's processing limit
        truncated_text = text[:max_length]

        # Construct the prompt
        prompt = f"Provide a one hundred word performance review along with a rating from 1-10 based on the following:\n\n{truncated_text}"

        # Send request to Ollama
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Clean the response by removing <think> tags (if any)
        full_response = response.get("message", {}).get("content", "").strip()
        cleaned_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL).strip()

        return cleaned_response
        
    except Exception as e:
        print(f"Error: {e}")
        return "An error occurred while generating the review."

# Summarize text function
def summarize_text(text):
    """
    Summarizes the provided text using Deepseek R1 via Ollama.
    """
    prompt = f"Summarize the following text briefly:\n\n{text}"
    
    response = ollama.chat(
        model="deepseek-r1:7b",
        messages=[{"role": "user", "content": prompt}]
    )
    
    summary = response["message"]["content"].strip()
    return summary

# Event: When the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# Command: Responds with "Pong!" when the user types "!ping"
@bot.command()
async def ping(ctx):
    await ctx.send("pong!")

# Command: Summarizes a user's thoughts using Ollama
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
    summary = summarize_text(thoughts_text)

    await ctx.send(f"Summary of {username}'s thoughts:\n{summary}")

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

            # Optionally, you can generate a performance review or summary of the video description (via Ollama)
            video = YouTube(shortURL)
            description = video.description
            summary = summarize_text(description)

            await message.channel.send(f"Summary of video description:\n{summary}")

        else:
            await message.channel.send("Error downloading the video.")

    # Ensure commands still work
    await bot.process_commands(message)

# Run the bot with the token from the .env file
bot.run(discord_token)
