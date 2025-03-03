import sqlite3

# Connect to the database
conn = sqlite3.connect("thoughts.db")
cursor = conn.cursor()

# Fetch all thoughts
cursor.execute("SELECT * FROM thoughts")
rows = cursor.fetchall()

# Display results
print("\n--- Thoughts Stored in Database ---\n")
for row in rows:
    print(f"ID: {row[0]}, User: {row[1]}, Thought: {row[2]}, Timestamp: {row[3]}")

# Close the connection
conn.close()
