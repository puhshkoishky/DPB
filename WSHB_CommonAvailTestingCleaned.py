# =================================================================================
#                           IMPORTING THE TOOLBOX
# =================================================================================
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import math
from datetime import datetime
import ollama
import re
from itertools import groupby

# =================================================================================
#                           THE BOT'S BRAIN: CLIENT CLASS
# =================================================================================
class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_conn = sqlite3.connect('WideShmeerBackend.db')
        self.initialize_database()

    def initialize_database(self):
        cursor = self.db_conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                preferred_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                degree_major TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS availability (
                user_id TEXT,
                day_of_week TEXT CHECK(day_of_week IN (
                    'Monday', 'Tuesday', 'Wednesday', 
                    'Thursday', 'Friday', 'Saturday', 'Sunday'
                )),
                start_time TEXT,
                end_time TEXT,
                PRIMARY KEY (user_id, day_of_week),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS common_availability (
                day_of_week TEXT,
                start_time TEXT,
                end_time TEXT,
                PRIMARY KEY (day_of_week, start_time, end_time)
            )
        ''')
        self.db_conn.commit()

    def time_to_minutes(self, time_str):
        if time_str == 'N/A':
            return None
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes

    def minutes_to_time(self, minutes):
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    def update_common_availability(self):
        """
        Compute common availability for each day using a sweep-line approach.
        A common time slot is one during which at least 75% (rounded up) of the users
        with valid availability for that day are available.
        This version groups events that occur at the same time and sorts events by time
        and by the change value (ensuring end events are processed before start events
        when they occur at the same timestamp) to correctly compute intersections.
        """
        cursor = self.db_conn.cursor()
        
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 
                        'Thursday', 'Friday', 'Saturday', 'Sunday']

        for day in days_of_week:
            cursor.execute('''
                SELECT start_time, end_time 
                FROM availability 
                WHERE day_of_week = ? 
                  AND start_time != 'N/A' 
                  AND end_time != 'N/A'
            ''', (day,))
            intervals = []
            for start, end in cursor.fetchall():
                start_min = self.time_to_minutes(start)
                end_min = self.time_to_minutes(end)
                if start_min is not None and end_min is not None:
                    intervals.append((start_min, end_min))
            
            # Calculate the threshold based only on users with valid availability for this day.
            valid_users = len(intervals)
            common_slots = []
            if valid_users > 0:
                required = math.ceil(0.75 * valid_users)
                # Build a list of events: +1 for a start, -1 for an end.
                events = []
                for s, e in intervals:
                    events.append((s, +1))
                    events.append((e, -1))
                # Sort events by time and then by -change (ensuring end events come before start events).
                events.sort(key=lambda x: (x[0], -x[1]))

                current_active = 0
                common_start = None

                # Group events with the same timestamp.
                for time, group in groupby(events, key=lambda x: x[0]):
                    delta = sum(change for _, change in group)
                    previous_active = current_active
                    current_active += delta

                    # When crossing the threshold upwards, mark the start.
                    if previous_active < required and current_active >= required:
                        common_start = time
                    # When dropping below threshold, mark the end.
                    elif previous_active >= required and current_active < required and common_start is not None:
                        common_slots.append((common_start, time))
                        common_start = None
                # Close any slot that remains open.
                if common_start is not None:
                    common_slots.append((common_start, 1440))
            
            # Clear existing common availability for the day.
            cursor.execute("DELETE FROM common_availability WHERE day_of_week = ?", (day,))
            # Insert the computed common slots.
            for start, end in common_slots:
                cursor.execute('''
                    INSERT INTO common_availability (day_of_week, start_time, end_time)
                    VALUES (?, ?, ?)
                ''', (day, self.minutes_to_time(start), self.minutes_to_time(end)))
        self.db_conn.commit()

    async def on_ready(self):
        print(f'Bot logged in as {self.user}!')
        try:
            # Replace with your actual server ID
            guild = discord.Object(id=*enter your server id here*)
            synced = await self.tree.sync(guild=guild)
            print(f'Successfully connected {len(synced)} commands to server')
        except Exception as e:
            print(f'Command sync error: {e}')

    async def on_message(self, message):
        if message.author == self.user:
            return
        print(f'Message from {message.author}: {message.content}')
        # Uncomment the next line if you use prefix commands:
        # await self.process_commands(message)

# =================================================================================
#                       SETTING UP BOT PERMISSIONS
# =================================================================================
intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)
# Replace with your actual server ID
GUILD_ID = discord.Object(id=*enter your server id here*)

# =================================================================================
#                       USER COMMANDS (SLASH COMMANDS)
# =================================================================================
@client.tree.command(
    name="register", 
    description="Save your name, contact info, and major",
    guild=GUILD_ID
)
@app_commands.describe(
    preferred_name="What you like to be called",
    email="Your email address",
    phone="Your phone number",
    major="Your study program (e.g., 'Computer Science')"
)
async def register(interaction: discord.Interaction, preferred_name: str, email: str, phone: str, major: str):
    user_id = str(interaction.user.id)
    try:
        cursor = client.db_conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, preferred_name, email, phone, major))
        
        days = ['Monday', 'Tuesday', 'Wednesday', 
                'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days:
            cursor.execute('''
                INSERT OR IGNORE INTO availability 
                VALUES (?, ?, 'N/A', 'N/A')
            ''', (user_id, day))
        client.db_conn.commit()
        await interaction.response.send_message("✅ Successfully registered!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Registration failed: {str(e)}")

@client.tree.command(
    name="set_availability", 
    description="Update your available times for a day (use N/A for unavailable)",
    guild=GUILD_ID
)
@app_commands.describe(
    day="Select a day",
    start_time="Start time (HH:MM or N/A)",
    end_time="End time (HH:MM or N/A)"
)
@app_commands.choices(day=[
    app_commands.Choice(name=d, value=d)
    for d in ['Monday', 'Tuesday', 'Wednesday', 
             'Thursday', 'Friday', 'Saturday', 'Sunday']
])
async def set_availability(interaction: discord.Interaction, day: str, start_time: str, end_time: str):
    user_id = str(interaction.user.id)
    start_time = start_time.upper()
    end_time = end_time.upper()

    if start_time == 'N/A' or end_time == 'N/A':
        if start_time != end_time:
            await interaction.response.send_message("❌ Both times must be N/A to mark unavailable")
            return
        start_time = end_time = 'N/A'
    else:
        try:
            datetime.strptime(start_time, "%H:%M")
            datetime.strptime(end_time, "%H:%M")
        except ValueError:
            await interaction.response.send_message("❌ Invalid format. Use HH:MM or N/A")
            return

    try:
        cursor = client.db_conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO availability 
            VALUES (?, ?, ?, ?)
        ''', (user_id, day, start_time, end_time))
        client.db_conn.commit()
        client.update_common_availability()
        
        if start_time == 'N/A':
            await interaction.response.send_message(f"✅ Marked {day} as unavailable")
        else:
            await interaction.response.send_message(f"✅ {day} availability set to {start_time}-{end_time}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}")

@client.tree.command(
    name="view_common", 
    description="Show time slots available to 75%+ users",
    guild=GUILD_ID
)
async def view_common(interaction: discord.Interaction):
    cursor = client.db_conn.cursor()
    cursor.execute('''
        SELECT day_of_week, start_time, end_time 
        FROM common_availability 
        ORDER BY 
            CASE day_of_week
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END,
            start_time
    ''')
    
    common_slots = cursor.fetchall()
    
    if not common_slots:
        await interaction.response.send_message("No common time slots available")
        return
    
    schedule = {}
    for day, start, end in common_slots:
        if day not in schedule:
            schedule[day] = []
        schedule[day].append(f"{start} - {end}")
    
    response = ["**Common Availability (75%+ Users Free)**"]
    days_order = ['Monday', 'Tuesday', 'Wednesday', 
                  'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day in days_order:
        if day in schedule:
            times = "\n".join(schedule[day])
            response.append(f"\n**{day}:**\n{times}")
        else:
            response.append(f"\n**{day}:** No common slots")
    
    await interaction.response.send_message("\n".join(response))

@client.tree.command(
    name="my_info", 
    description="View your registered information",
    guild=GUILD_ID
)
async def my_info(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    cursor = client.db_conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        response = (
            "**Your Information**\n"
            f"Name: {user[1]}\n"
            f"Email: {user[2]}\n"
            f"Phone: {user[3]}\n"
            f"Major: {user[4]}"
        )
    else:
        response = "❌ You're not registered! Use `/register` first"
    await interaction.response.send_message(response)

# =================================================================================
#                       AI REVIEW FEATURE
# =================================================================================
def LLMReviewRequest(text, model="deepseek-r1:7b", max_length=300):
    try:
        truncated_text = text[:max_length]
        prompt = f"Provide a 100-word performance review with 1-10 rating based on:\n\n{truncated_text}"
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        full_response = response.get("message", {}).get("content", "").strip()
        cleaned_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL).strip()
        return cleaned_response
    except Exception as e:
        print(f"AI Service Error: {e}")
        return "⚠️ Our AI is currently unavailable. Please try again later!"

@client.tree.command(
    name="perform_review", 
    description="Get AI feedback on your text (max 300 words)",
    guild=GUILD_ID
)
async def perform_review(interaction: discord.Interaction, description: str):
    await interaction.response.defer()
    review = LLMReviewRequest(description)
    await interaction.followup.send(f'**AI Review:**\n{review}')

# =================================================================================
#                       STARTING THE BOT ENGINE
# =================================================================================
# Replace the placeholder with your actual bot token
client.run('-')
