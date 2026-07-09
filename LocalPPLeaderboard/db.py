import sqlite3

connection = sqlite3.connect("user.db")
cur = connection.cursor()

## clear the table (for testing purposes)
cur.execute(
    """
    DELETE FROM users
    WHERE 1=1
    """
)

connection.commit()

cur.execute(
    """
    INSERT INTO users (discord_id, osu_id)
    VALUES(?, ?)
    """, (2,2)
)
cur.execute(
    """
    INSERT INTO users (discord_id, osu_id)
    VALUES(?, ?)
    """, (1,1)
)


connection.commit()
for row in cur.execute(""" SELECT * FROM users"""):
    print(row)
connection.close()


