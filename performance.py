import discord
import sqlite3
import requests
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Database Setup (Runs Once)
def setup_database():
    conn = sqlite3.connect("thoughts.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS thoughts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            thought TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

setup_database()

# Command: Saves a thought to SQL
@bot.command()
async def thoughts(ctx, *, thought: str):
    """Saves a user's thought into the SQLite database"""
    conn = sqlite3.connect("thoughts.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO thoughts (user, thought, timestamp) VALUES (?, ?, ?)", 
                   (ctx.author.name, thought, ctx.message.created_at))
    conn.commit()
    conn.close()
    
    await ctx.send(f"Your thought has been saved, {ctx.author.name}!")

# Command: Retrieves recent thoughts
@bot.command()
async def read(ctx):
    """Retrieves and displays the last 5 thoughts from the database"""
    conn = sqlite3.connect("thoughts.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user, thought, timestamp FROM thoughts ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()

    if rows:
        thoughts_message = "\n".join([f"{row[0]}: {row[1]} ({row[2]})" for row in rows])
        await ctx.send(f"Here are the latest thoughts:\n```{thoughts_message}```")
    else:
        await ctx.send("No thoughts recorded yet.")

# Command: Clear the Database
@bot.command()
async def clear(ctx):
    """Clears all thoughts from the database"""
    conn = sqlite3.connect("thoughts.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM thoughts")
    conn.commit()
    conn.close()

    await ctx.send("All thoughts have been cleared.")

# Command: Summarize Thoughts using AI
@bot.command()
async def analyze(ctx):
    """Analyzes stored thoughts and provides a summary"""
    conn = sqlite3.connect("thoughts.db")
    cursor = conn.cursor()
    cursor.execute("SELECT thought FROM thoughts")
    thoughts_list = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not thoughts_list:
        await ctx.send("No thoughts to analyze.")
        return

    thoughts_text = " ".join(thoughts_list)

    # AI API Request
    api_key = ""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [{"role": "user", "content": f"Summarize the following thoughts: {thoughts_text}"}]
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        summary = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        await ctx.send(f"Thoughts summary:\n```{summary}```")
    else:
        await ctx.send("Sorry, the analysis request failed.")

bot.run("")
