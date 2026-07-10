import sqlite3
import osu

score_table_order = "user_id, username, beatmap_id, beatmap, play_max_combo, beatmap_max_combo, mods, score, pp, accuracy"
score_question = "?, ?, ?, ?, ?, ?, ?, ?, ?"

class UserDB:
    def __init__(self, db_name):
        self.db_name = db_name
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    discord_id INTEGER PRIMARY KEY,
                    osu_id INTEGER NOT NULL UNIQUE
                );
            """)
    
    def __str__(self):
            with sqlite3.connect(self.db_name) as connection:
                cur = connection.cursor()
                results = cur.execute("SELECT * FROM users;")

                return_str = ""
                for row in results.fetchall():
                    return_str += f"discord_id: {row[0]}, osu_id: {row[1]}\n"

                return return_str

        
    def add_user(self, discord_id, osu_id):
        try:
            d_id = int(discord_id)
            o_id = int(osu_id)
        except ValueError:
            print("Invalid inputs for Discord ID and osu! ID. No value added.")
            return

        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            try:
                cur.execute(
                """
                INSERT INTO users (discord_id, osu_id)
                VALUES(?, ?);
                """, (d_id, o_id)
                )
                return True

            except sqlite3.IntegrityError as error:
                print(f"Could not add user: {error}")
                return False
    
    def delete_table(self):
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()
            cur.execute("DROP TABLE IF EXISTS users;")

    def clear_records(self):
        with sqlite3.connect(self.db_name) as connection:
            try:
                cur = connection.cursor()
                cur.execute("""DELETE FROM users""")
                return True
            except sqlite3.InternalError as error:
                print(f"Could not clear user database: {error}")
                return False
    
    def get_osu_id(self, discord_id):
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()
            res = cur.execute(
                "SELECT osu_id FROM users WHERE discord_id = ?;",
                (int(discord_id),)
            )

            row = res.fetchone()

            if row is None:
                return None

            return row[0]



class OsuScoreDB:
    def __init__(self, db_name, osu_client: osu.Client):
        self.db_name = db_name
        self.client = osu_client

        with sqlite3.connect(self.db_name) as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            cur = connection.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    beatmap_id INTEGER NOT NULL,
                    beatmap TEXT NOT NULL,
                    play_max_combo INTEGER NOT NULL,
                    beatmap_max_combo INTEGER,
                    mods TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    pp REAL NOT NULL,
                    accuracy REAL NOT NULL,
                    counting INTEGER NOT NULL CHECK(counting = 0 OR counting = 1) DEFAULT 1,

                    PRIMARY KEY (user_id, beatmap_id),
                    FOREIGN KEY (user_id) REFERENCES users(osu_id)
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_pp
                ON scores (pp DESC);
            """)

    def __str__(self):
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()
            results = cur.execute("""
                SELECT
                    user_id,
                    username,
                    beatmap_id,
                    beatmap,
                    play_max_combo,
                    beatmap_max_combo,
                    mods,
                    score,
                    pp,
                    accuracy,
                    counting
                FROM scores
                ORDER BY pp DESC;
            """)

            return_str = ""

            for row in results.fetchall():
                return_str += (
                    f"user_id: {row[0]}, "
                    f"username: {row[1]}, "
                    f"beatmap_id: {row[2]}, "
                    f"beatmap: {row[3]}, "
                    f"combo: {row[4]}/{row[5]}, "
                    f"mods: {row[6]}, "
                    f"score: {row[7]}, "
                    f"pp: {row[8]}, "
                    f"accuracy: {row[9]}, "
                    f"counting: {row[10]}\n"
                )

            return return_str

    def get_score_from_id(self, score_id: int):
        ## DIDNT USE THIS, MIGHT NOT BE NEEDED
        score = self.client.get_score_by_id("osu", score_id)
        return score

    def get_beatmap_max_from_id(self, beatmap_id: int):
        beatmap = self.client.get_beatmap(beatmap_id)
        return beatmap.max_combo

    def clear_records(self):
        with sqlite3.connect(self.db_name) as connection:
            try:
                cur = connection.cursor()
                cur.execute("DELETE FROM scores;")
                return True
            except sqlite3.Error as error:
                print(f"Could not clear score database: {error}")
                return False

    def add_score(self, score_object: osu.objects.SoloScore):
        """Retrieves score information and adds it to the database."""

        if score_object.pp is None:
            print("Could not add score: score has no pp value.")
            return False

        if score_object.beatmap_id is None:
            print("Could not add score: score has no beatmap_id.")
            return False

        username = ""
        if score_object.user is not None:
            username = score_object.user.username

        beatmap_name = ""
        if score_object.beatmap is not None:
            beatmap_name = self.get_beatmap_display_name(score_object)

        beatmap_max_combo = self.get_beatmap_max_from_id(score_object.beatmap_id)

        with sqlite3.connect(self.db_name) as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            cur = connection.cursor()

            try:
                cur.execute("""
                    INSERT INTO scores (
                        user_id,
                        username,
                        beatmap_id,
                        beatmap,
                        play_max_combo,
                        beatmap_max_combo,
                        mods,
                        score,
                        pp,
                        accuracy
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, beatmap_id)
                    DO UPDATE SET
                        username = excluded.username,
                        beatmap = excluded.beatmap,
                        play_max_combo = excluded.play_max_combo,
                        beatmap_max_combo = excluded.beatmap_max_combo,
                        mods = excluded.mods,
                        score = excluded.score,
                        pp = excluded.pp,
                        accuracy = excluded.accuracy
                    WHERE scores.pp < excluded.pp;
                """, (
                    score_object.user_id,
                    username,
                    score_object.beatmap_id,
                    beatmap_name,
                    score_object.max_combo,
                    beatmap_max_combo,
                    str(score_object.mods),
                    score_object.total_score,
                    score_object.pp,
                    score_object.accuracy
                ))

                return True

            except sqlite3.IntegrityError as error:
                print(f"Could not add score: {error}")
                return False
            
    def get_recent_score(self, user_id:int, pos=0):
        return self.client.get_user_scores(user_id, osu.UserScoreType.RECENT, include_fails=False, limit=1)
    
    def get_beatmap_display_name(self, score_object: osu.objects.SoloScore):
        if score_object.beatmapset is None or score_object.beatmap is None:
            return f"beatmap_id={score_object.beatmap_id}"

        artist = score_object.beatmapset.artist
        title = score_object.beatmapset.title
        version = score_object.beatmap.version

        return f"{artist} - {title} [{version}]"
    
    def calculate_leaderboard_pp(self, weighting:float) -> float:
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()
            res = cur.execute("""
                SELECT pp
                FROM scores
                ORDER BY pp DESC LIMIT 100;
                        """)
            
            total = 0
            cur_weighting = 1
            for row in res.fetchall():
                total += row[0] * cur_weighting
                cur_weighting *= weighting
            
        return total



# class JointPPLeaderboardDB(osuScoreDB):
#     def __init__(self):
#         pass


    
# class osuScoreDB:
#     def __init__(self, db_name, osu_client : osu.Client):
#         self.db_name = db_name
#         self.client = osu_client

#         with sqlite3.connect(self.db_name) as connection:
#             cur = connection.cursor()
#             connection.execute("""PRAGMA foreign_keys = ON;""")
#             cur.execute("""
#                     CREATE TABLE IF NOT EXISTS scores (
#                         user_id INTEGER NOT NULL,
#                         username TEXT NOT NULL,
#                         beatmap_id INTEGER NOT NULL,
#                         beatmap TEXT NOT NULL,
#                         play_max_combo INTEGER NOT NULL,
#                         beatmap_max_combo INTEGER,
#                         mods TEXT NOT NULL,
#                         score INTEGER NOT NULL,
#                         pp REAL NOT NULL,
#                         accuracy REAL NOT NULL,
#                         counting INTEGER NOT NULL CHECK(counting = 0 OR counting = 1) DEFAULT 1,

#                         PRIMARY KEY (user_id, beatmap_id),
#                         FORIEGN KEY (user_id) REFERENCES users(osu_id)
#                     );
#             """)
#             cur.execute("""
#                 CREATE INDEX IF NOT EXISTS idx_pp ON scores (pp DESC);
#             """)

#     def __str__(self):
#         with sqlite3.connect(self.db_name) as connection:
#             cur = connection.cursor()
#             results = cur.execute("""
#                 SELECT
#                     user_id,
#                     username,
#                     beatmap_id,
#                     beatmap,
#                     play_max_combo,
#                     beatmap_max_combo,
#                     mods,
#                     score,
#                     pp,
#                     accuracy
#                 FROM scores
#                 ORDER BY pp DESC;
#             """)

#             return_str = ""

#             for row in results.fetchall():
#                 return_str += (
#                     f"user_id: {row[0]}, "
#                     f"username: {row[1]}, "
#                     f"beatmap_id: {row[2]}, "
#                     f"beatmap: {row[3]}, "
#                     f"combo: {row[4]}/{row[5]}, "
#                     f"mods: {row[6]}, "
#                     f"score: {row[7]}, "
#                     f"pp: {row[8]}, "
#                     f"accuracy: {row[9]}\n"
#                 )

#             return return_str
        
#     def get_score_from_id(self, score_id: int):
#         score: osu.object.SoloScore = self.client.get_score_by_id("osu", score_id)
#         return score

#     def get_beatmap_max_from_id(self, beatmap_id: int):
#         return self.client.get_beatmap(beatmap_id).max_combo
    
#     def clear_records(self):
#         with sqlite3.connect(self.db_name) as connection:
#             try:
#                 cur = connection.cursor()
#                 cur.execute("""DELETE FROM score""")
#                 return True
#             except sqlite3.InternalError as error:
#                 print(f"Could not clear user database: {error}")
#                 return False

#     def add_score(self, score_object: osu.objects.SoloScore):
#         """ PUBLIC: Retreives score information and adds it to the DB """
#         with sqlite3.connect(self.db_name) as connection:
#             cur = connection.cursor()

#             try:
#                 cur.execute(f"""
#                 INSERT INTO scores (
#                     user_id,
#                     username,
#                     beatmap_id,
#                     beatmap,
#                     play_max_combo,
#                     beatmap_max_combo,
#                     mods,
#                     score,
#                     pp,
#                     accuracy
#                 )
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                 ON CONFLICT(user_id, beatmap_id)
#                 DO UPDATE SET
#                       username = excluded.username,
#                     play_max_combo = excluded.play_max_combo,
#                     beatmap_max_combo = excluded.beatmap_max_combo,
#                     mods = excluded.mods,
#                     score = excluded.score,
#                     pp = excluded.pp,
#                     accuracy = excluded.accuracy      
#                 WHERE scores.pp < excluded.pp;
#                 """, (score_object.user_id, score_object.user, score_object.beatmap_id, 
#                       score_object.beatmap, score_object.max_combo, self.get_beatmap_max_from_id(score_object.beatmap_id), 
#                       str(score_object.mods), score_object.pp, score_object.accuracy
#                       ))
#                 return True

#             except sqlite3.IntegrityError as error:
#                 print(f"Could not add user: {error}")
#                 return False
            

#         pass
