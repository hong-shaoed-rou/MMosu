import sqlite3
from collections import defaultdict
import os
import osu
import time
from dotenv import find_dotenv, load_dotenv

class UserDB:
    def __init__(self, db_name, osu_client: osu.Client):
        self.db_name = db_name
        self.client = osu_client

        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    discord_id INTEGER PRIMARY KEY,
                    osu_id INTEGER NOT NULL UNIQUE,
                    osu_username TEXT NOT NULL,
                    team TEXT NOT NULL
                );
            """)
    
    def __str__(self):
            with sqlite3.connect(self.db_name) as connection:
                cur = connection.cursor()
                results = cur.execute("SELECT * FROM users;")

                return_str = ""
                for row in results.fetchall():
                    return_str += f"discord_id: {row[0]}, osu_id: {row[1]}, osu_username: {row[2]}, team: {row[3]}\n"

                return return_str

        
    def add_user(self, discord_id:str, osu_id:str, team="teamless"):
        try:            
            
            d_id = int(discord_id)
            o_id = int(osu_id)

        except ValueError as error:
            print(f" {error}: Invalid inputs for Discord ID, osu! ID, or Team. User could not be added, please try again.")
            return False

        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            try:
                osu_username = self.client.get_user(o_id).username

                cur.execute(
                """
                INSERT INTO users (discord_id, osu_id, osu_username, team)
                VALUES(?, ?, ?, ?);
                """, (d_id, o_id, osu_username, team))

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
                    beatmap_id INTEGER NOT NULL,
                    score_id INTEGER NOT NULL,
                    team TEXT,

                    beatmap TEXT NOT NULL,    
                    username TEXT NOT NULL,
                    
                    play_max_combo INTEGER NOT NULL,
                    beatmap_max_combo INTEGER,
                    
                    score INTEGER NOT NULL,
                    pp REAL NOT NULL,
                    accuracy REAL NOT NULL,
                    mods TEXT NOT NULL,
                    
                    counting INTEGER NOT NULL CHECK(counting = 0 OR counting = 1) DEFAULT 1,

                    PRIMARY KEY (user_id, beatmap_id),
                    FOREIGN KEY (user_id) REFERENCES users(osu_id)
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_pp
                ON scores (pp DESC);
            """)

            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_score_id
                ON scores(score_id);
                        """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS beatmap_meta (
                        
                    beatmap_id INTEGER PRIMARY KEY,
                    song_title TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    
                    star_rating FLOAT,
                    mode TEXT NOT NULL,
                    length INTEGER NOT NULL,
                    max_combo INTEGER NOT NULL,
                    bpm FLOAT NOT NULL,
                    cs FLOAT NOT NULL,
                    ar FLOAT NOT NULL,
                    ranked_date TEXT,
                    
                    mapper TEXT NOT NULL,
                    tags TEXT,
                    genre TEXT,
                    count_user_plays INTEGER NOT NULL,
                    total_obj INTEGER NOT NULL,
                        
                    background BLOB
                    
                );
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

    def add_beatmap_to_beatmap_metadata(self, beatmap_id: int):
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            try:
                beatmap = self.client.get_beatmap(beatmap_id)
            except Exception as error:
                print(f"Could not fetch beatmap {beatmap_id}: {error}")
                return False

            if beatmap is None:
                print("Could not find beatmap")
                return False

            beatmapset = beatmap.beatmapset

            if beatmapset is None:
                print("Could not find beatmapset metadata")
                return False

            try:
                cur.execute("""
                    INSERT INTO beatmap_meta (
                        beatmap_id,
                        song_title,
                        difficulty,
                        artist,

                        star_rating,
                        mode,
                        length,
                        max_combo,
                        bpm,
                        cs,
                        ar,
                        ranked_date,

                        mapper,
                        tags,
                        genre,
                        count_user_plays,
                        total_obj
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(beatmap_id) DO NOTHING;
                """, (
                    beatmap.id,
                    beatmapset.title,
                    beatmap.version,
                    beatmapset.artist,

                    beatmap.difficulty_rating,
                    str(beatmap.mode),
                    beatmap.hit_length,
                    beatmap.max_combo,
                    beatmap.bpm,
                    beatmap.cs,
                    beatmap.ar,
                    str(beatmapset.ranked_date),

                    beatmap.owners[0].id,
                    beatmapset.tags,
                    str(beatmapset.genre),
                    beatmap.playcount,
                    beatmap.count_circles + beatmap.count_sliders + beatmap.count_spinners
                ))

                return True

            except sqlite3.Error as error:
                print(f"Could not add beatmap metadata: {error}")
                return False

    def add_score(self, score_object: osu.objects.SoloScore):
        """Retrieves score information and adds it to the database."""

        if score_object.beatmap_id is None:
            print("Could not add score: score has no beatmap_id.")
            return False
        
        if score_object.pp is None:
            print("Could not add score: score has no pp value.")
            return False


        ## TO BE FIXED LATER WITH THE NEW METADATA DB
        username = score_object.user.username
        beatmap_name = self.get_beatmap_display_name(score_object)
        beatmap_max_combo = self.get_beatmap_max_from_id(score_object.beatmap_id)

        self.add_beatmap_to_beatmap_metadata(score_object.beatmap_id)

        with sqlite3.connect(self.db_name) as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            cur = connection.cursor()

            try:
                score_id = int(score_object.id)

                res = cur.execute("""
                    SELECT EXISTS(
                        SELECT 1
                        FROM scores
                        WHERE score_id = ?
                    );
                """, (score_id,))

                already_exists = res.fetchone()[0]

                if already_exists:
                    print("score already submitted")
                    return False
                
                team = cur.execute("""SELECT team FROM users WHERE osu_id = ?""", (score_object.user_id,)) .fetchone()[0]
            
                
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
                        accuracy,
                        score_id,
                        team
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    score_object.user.username,
                    score_object.beatmap_id,
                    beatmap_name,
                    score_object.max_combo,
                    beatmap_max_combo,
                    str(score_object.mods),
                    score_object.total_score,
                    score_object.pp,
                    score_object.accuracy,
                    score_object.id,
                    team

                ))

                return True

            except sqlite3.IntegrityError as error:
                print(f"Could not add score: {error}")
                return False
            
    def get_recent_score(self, user_id:int, pos=0):
        return self.client.get_user_scores(user_id, osu.UserScoreType.RECENT, include_fails=False, limit=1 + pos)
    
    def get_beatmap_display_name(self, score_object: osu.objects.SoloScore):
        artist = score_object.beatmapset.artist
        title = score_object.beatmapset.title
        version = score_object.beatmap.version

        return f"{artist} - {title} [{version}]"
    
    def calculate_leaderboard_pp(self, weighting:float, max_num_scores:int, max_num_player_score:int) -> float:
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            teams = cur.execute("""SELECT DISTINCT team FROM scores""").fetchall()
            scores = {team : 0 for team in teams}

            for team in teams:
                res = cur.execute(f"""
                    SELECT *
                    FROM scores
                    WHERE counting = 1 AND team = ?;""", team)
            
                player_scores_counted = defaultdict(int)
                counted_maps = set()
                counted_scores = 0
                cur_weighting = 1

                for row in res.fetchall():
                    if counted_scores > max_num_scores: break


                    user_id = row[0]
                    beatmap_id = row[1]
                    pp = row[9]

                    if ((beatmap_id in counted_maps) or player_scores_counted[user_id] > max_num_player_score):
                        continue
                    else:
                        counted_maps.add(beatmap_id)
                        player_scores_counted[user_id] += 1
                        
                        scores[team] += pp * cur_weighting
                        counted_scores += 1
                        cur_weighting *= weighting

            for key,val in scores.items():
                print(f"team {key}: {val}pp")

        return 1 # need to update the bot function as out-value has changed
    
    def pretty_print(self):
        print("\n==============================")
        print("PRINTING ALL VALUES IN DATABASE")
        print("==============================")

        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            print("\n--- SAVED SCORES ---")
            score_lb = cur.execute("SELECT * FROM scores;")
            score_columns = [description[0] for description in score_lb.description]

            score_rows = score_lb.fetchall()

            if len(score_rows) == 0:
                print("No saved scores.")
            else:
                for i, row in enumerate(score_rows, start=1):
                    print(f"\nScore #{i}")
                    print("-" * 20)

                    for column_name, value in zip(score_columns, row):
                        print(f"{column_name}: {value}")

            print("\n--- SAVED BEATMAPS ---")
            beat_md = cur.execute("SELECT * FROM beatmap_meta;")
            beatmap_columns = [description[0] for description in beat_md.description]

            beatmap_rows = beat_md.fetchall()

            if len(beatmap_rows) == 0:
                print("No saved beatmaps.")
            else:
                for i, row in enumerate(beatmap_rows, start=1):
                    print(f"\nBeatmap #{i}")
                    print("-" * 20)

                    for column_name, value in zip(beatmap_columns, row):
                        print(f"{column_name}: {value}")



if (__name__ == "__main__"):
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    client_id = int(os.environ["client_id"])
    client_secret = os.environ["client_secret"]
    redirect_url = "http://127.0.0.1:8080"
    key = os.environ["DISCORD_API_KEY"]
    osu_client = osu.Client.from_credentials(client_id, client_secret, redirect_url)
    db = OsuScoreDB("mmosu.db", osu_client)

    user_id = 11955716

    top_scores = osu_client.get_user_scores(
        user_id,
        osu.UserScoreType.BEST,
        limit=10
    )
    # db.clear_records()

    # for i, score in enumerate(top_scores, start=1):
    #     print(f"Adding score {i}/10: {score.pp}pp on beatmap {score.beatmap_id}")
    #     db.add_score(score)
    #     # time.sleep(1)

    # db.pretty_print()

    print(db.calculate_leaderboard_pp(0.95, 10, 5))


    pass
