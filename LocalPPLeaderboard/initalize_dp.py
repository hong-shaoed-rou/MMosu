"""
The purpose of this program is to create a new database to store user data for linking
"""

import sqlite3

connection = sqlite3.connect("user.db")
cur = connection.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    discord_id UNSIGNED BIG INT NOT NULL PRIMARY KEY,
    osu_id INT NOT NULL UNIQUE
)
"""
)
connection.commit()

res = cur.execute("SELECT name FROM sqlite_master")
print(res.fetchall())
connection.close()



