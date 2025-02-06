import sqlite3
import os

db_path = 'users.db'

if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted existing database file: {db_path}")

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('''CREATE TABLE users
             (email TEXT PRIMARY KEY, username TEXT, date INT, valid INT)''')

# users = [
#     ("k.aferiad@ensam.ac.ma", "k.aferiad", 1738516182, 2),
# ]

# c.executemany('INSERT INTO users VALUES (?, ?, ?, ?)', users)

conn.commit()
conn.close()

print(f"Created new database file: {db_path}")