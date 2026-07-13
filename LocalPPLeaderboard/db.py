import sqlite3
from collections import defaultdict
import os
import osu
import datetime
import time
from dotenv import find_dotenv, load_dotenv

class UserDB:
    def __init__(self, db_name, osu_client: osu.Client, autofill=True):
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
    def __init__(self, db_name, osu_client: osu.Client, autofill=True):
        self.db_name = db_name
        self.client = osu_client
        self.autofill = autofill

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
                    miss_count INT NOT NULL,
                    
                    counting INTEGER NOT NULL CHECK(counting = 0 OR counting = 1) DEFAULT 1,
                    submitted_at TEXT NOT NULL,

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
                CREATE INDEX IF NOT EXISTS idx_beatmap_pp
                ON scores (beatmap_id, pp DESC);
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
                    counting,
                    miss_count,
                    submitted_at
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
                    f"misscount: {row[11]}, "
                    f"mods: {row[6]}, "
                    f"score: {row[7]}, "
                    f"pp: {row[8]}, "
                    f"accuracy: {row[9]}, "
                    f"submitted at: {row[12]}"
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

            already_exists = cur.execute(
                """
                SELECT 1
                FROM beatmap_meta
                WHERE beatmap_id = ?
                LIMIT 1;
                """,
                (beatmap_id,)
            ).fetchone()

            if already_exists is not None:
                return True

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
            
    def get_beatmamp_display_name(self, beatmap_id:int) -> str:
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            try: 
                res = cur.execute("""SELECT artist, song_title, difficulty FROM beatmap_meta WHERE beatmap_id = ?""", (beatmap_id,)).fetchone()
                artist, title, version = res[0], res[1], res[2]
                return f"{artist} - {title} [{version}]"

            except sqlite3.IntegrityError as Error:
                print(f"Could not find beatmap_id or  artist, title, or difficulty for the beatmap in the database: {Error}")
                return False

    def score_exists_in_db(self, score_id:int) -> bool:
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            try:
                res = cur.execute("""
                        SELECT EXISTS(
                            SELECT 1
                            FROM scores
                            WHERE score_id = ?
                        );
                    """, (score_id,))

                ## NOTE: EXISTS is a subquery which returns 1 or 0, from which SELECT grabs
                if res.fetchone()[0] == 1:
                    return True
                else:
                    return False
                
            except sqlite3.IntegrityError as Error:
                print(f"Error while checking for score: {Error}")
                return



    def _get_attribute_from_id(self, attribute:str, beatmap_id:int) -> str:
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()
            try: 
                res = cur.execute("""SELECT ? FROM beatmap_meta WHERE beatmap_id = ?""",(attribute, beatmap_id)).fetchone()[0]
                return str(res)

            except sqlite3.IntegrityError as Error:
                print(f"Could not find beatmap_id or name attributes in the database: {Error}")
                return False

    def add_score(self, score_object: osu.objects.SoloScore):
        if score_object.beatmap_id is None:
            print("Could not add score: score has no beatmap_id.")
            return False
        elif score_object.pp is None:
            print("Could not add score: score has no pp value.")
            return False
        else:
            if self.score_exists_in_db(score_object.id):
                print("Score already submitted")
                return False
                
            self.add_beatmap_to_beatmap_metadata(score_object.beatmap_id)

        username = score_object.user.username
        beatmap_name = self.get_beatmamp_display_name(score_object.beatmap_id)
        beatmap_max_combo = self._get_attribute_from_id("max_combo", score_object.beatmap_id)

        miss_count = score_object.statistics.miss if score_object.statistics.miss is not None else 0
        submitted_at = str(datetime.datetime.now())

        with sqlite3.connect(self.db_name) as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            cur = connection.cursor()

            try:
                res = self.get_top_score_on_beatmap(score_object.beatmap_id)
                if res is not False:
                    f_username, f_pp, f_score_id = res
                    if f_pp < score_object.pp:
                        print(f"{f_username}'s score on {self.get_beatmamp_display_name(score_object.beatmap_id)} was sniped by {username}!!!")

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
                        team,
                        miss_count,
                        submitted_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, beatmap_id)
                    DO UPDATE SET
                        username = excluded.username,
                        beatmap = excluded.beatmap,
                        play_max_combo = excluded.play_max_combo,
                        beatmap_max_combo = excluded.beatmap_max_combo,
                        mods = excluded.mods,
                        score = excluded.score,
                        pp = excluded.pp,
                        accuracy = excluded.accuracy,
                        score_id = excluded.score_id,
                        miss_count = excluded.miss_count,
                        submitted_at = excluded.submitted_at
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
                    team,
                    miss_count,
                    submitted_at

                ))

                if not(self.autofill):
                    self.update_counting_on_beatmap(cur, score_object.beatmap_id)

                return True

            except sqlite3.IntegrityError as error:
                print(f"Could not add score: {error}")
                return False
            
    def get_recent_score(self, user_id:int, pos=0):
        return self.client.get_user_scores(user_id, osu.UserScoreType.RECENT, include_fails=False, limit=1 + pos)
    
    def get_top_score_on_beatmap(self, beatmap_id:int):
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            res = cur.execute("""SELECT username, pp, score_id 
                        FROM scores
                        WHERE beatmap_id = ? 
                        ORDER BY pp DESC 
                        LIMIT 1""", (beatmap_id,)).fetchone()
            
            if res is None:
                # print(f"No score on the beatmap {beatmap_id} currently exists")
                return False
            
            # print(f"The current best score on {beatmap_id} is {res[0]}'s score worth {res[1]}pp!")
            return(res)
    
    
    def calculate_leaderboard_pp(self, weighting: float, max_num_scores: int, max_num_player_score: int) -> dict[str, float]:

        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            teams = [row[0] for row in cur.execute("SELECT DISTINCT team FROM scores;").fetchall()]

            team_scores = {team: 0.0 for team in teams}
            team_score_counts = {team: 0 for team in teams} # how many times a team has had their score added
            team_weightings = {team: 1.0 for team in teams}

            player_scores_counted = defaultdict(int)
            counted_maps = set()

            rows = cur.execute(
                    """
                    SELECT
                        user_id,
                        beatmap_id,
                        team,
                        pp,
                        submitted_at,
                        score_id
                    FROM scores
                    WHERE counting = 1
                    ORDER BY
                        pp DESC,
                        submitted_at ASC,
                        score_id ASC;
                    """
                ).fetchall()

            for (user_id, beatmap_id, team, pp, submitted_at, score_id) in rows:

                if beatmap_id in counted_maps:
                    continue

                if player_scores_counted[user_id] >= max_num_player_score:
                    continue

                if team_score_counts[team] >= max_num_scores:
                    continue

                counted_maps.add(beatmap_id)
                player_scores_counted[user_id] += 1

                team_scores[team] += pp * team_weightings[team]
                team_score_counts[team] += 1
                team_weightings[team] *= weighting

            for team, total_pp in team_scores.items():
                print(f"team {team}: {total_pp}pp")

            return team_scores

    def update_counting_on_beatmap(self, cur:sqlite3.Connection.cursor, beatmap_id:int) -> None:

            # Turns off counting for all beatmaps
        cur.execute("""
                UPDATE scores 
                SET counting = 0
                WHERE beatmap_id = ?""", (beatmap_id,))
        
        cur.execute("""
                UPDATE scores
                SET counting = 1
                WHERE score_id = (
                        SELECT score_id
                        FROM scores
                        WHERE beatmap_id = ?
                        ORDER BY pp DESC, submitted_at ASC, score_id ASC
                        LIMIT 1
                    )
        """, (beatmap_id,))
            

    
    def pretty_print(self):
        print("\n==============================")
        print("PRINTING ALL VALUES IN DATABASE")
        print("==============================")

        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            print("\n--- SAVED SCORES ---")
            score_lb = cur.execute("SELECT * FROM scores ORDER BY pp DESC;")
            score_columns = [description[0] for description in score_lb.description]

            score_rows = score_lb.fetchall()

            if len(score_rows) == 0:
                print("No saved scores.")
            else:
                for i, row in enumerate(score_rows, start=1):
                    if i > 10: break
                    print(f"\nScore #{i}")
                    print("-" * 20)

                    for column_name, value in zip(score_columns, row):
                        print(f"{column_name}: {value}")



if __name__ == "__main__":
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)

    client_id = int(os.environ["client_id"])
    client_secret = os.environ["client_secret"]
    redirect_url = "http://127.0.0.1:8080"

    osu_client = osu.Client.from_credentials(
        client_id,
        client_secret,
        redirect_url
    )

    db = OsuScoreDB("mmosu.db", osu_client,True)
    udb = UserDB("mmosu.db", osu_client)

    db.pretty_print()

    players = [
    # Red team
    (1, 7562902, "red"),           # mrekk

    # Blue team
    (2, 14715160, "blue"),         # cryshina
    (3, 15406985, "blue"),         # Ivaxa
    (4, 9269034, "blue"),          # Akolibed
    (5, 10549880, "blue"),         # NINERIK
    (6, 13108233, "blue"),         # milosz
    (7, 11367222, "blue"),         # lifeline
    (8, 12779141, "blue"),         # gnahus
    (9, 4175698, "blue"),          # sytho
    (10, 13211727, "blue"),        # NyanPotato
    (11, 5033077, "blue"),         # Zylice
    (12, 12137295, "blue"),        # jahkon
    (13, 21207816, "blue"),        # bored yes
    (14, 8251785, "blue"),         # killer2007
    (15, 6404583, "blue"),         # PLOXARU
    (16, 25444680, "blue"),        # androgenic / originset
    (17, 19851850, "blue"),        # cloppit
    (18, 11496364, "blue"),        # JappaDeKappa
    (19, 6725771, "blue"),         # Cloudpaw
    (20, 12834269, "blue"),        # roaz
    ]

    db.clear_records()
    udb.clear_records()

    print("Adding users")

    for discord_id, osu_id, team in players:
        added = udb.add_user(
            discord_id=discord_id,
            osu_id=osu_id,
            team=team
        )

        if added:
            print(f"Added osu! user {osu_id} to team {team}")
        else:
            print(f"Could not add osu! user {osu_id}")

    print("\nGoing through player scores")

    total_scores_added = 0

    for player_number, (_, osu_id, team) in enumerate(
        players,
        start=1
    ):
        print(
            f"\nFetching player {player_number}/{len(players)}: "
            f"{osu_id} ({team})"
        )

        try:
            top_scores = osu_client.get_user_scores(
                osu_id,
                osu.UserScoreType.BEST,
                limit=100,
                mode='osu'
            )
        except Exception as error:
            print(f"Could not retrieve scores for {osu_id}: {error}")
            continue

        score_count = len(top_scores)

        for score_number, score in enumerate(top_scores, start=1):
            print(
                f"Adding score {score_number}/{score_count} "
                f"for user {osu_id}: "
                f"{score.pp}pp on beatmap {score.beatmap_id}"
            )

            if db.add_score(score):
                total_scores_added += 1

    print(f"\nSuccessfully added {total_scores_added} scores")

    print("\n--- LEADERBOARD RESULTS ---")
    db.calculate_leaderboard_pp(
        weighting=0.95,
        max_num_scores=100,
        max_num_player_score=100
    )
