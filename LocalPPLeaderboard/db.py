import sqlite3
from collections import defaultdict
import os
import osu
import datetime
from dotenv import find_dotenv, load_dotenv

class ScoreFilter:
    def __init__(self):
        pass

class ModMultiplier:
    def __init__(self):
        pass

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

        try:
            with sqlite3.connect(self.db_name) as connection:
                cur = connection.cursor()


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
        try:
            with sqlite3.connect(self.db_name) as connection:
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
    def __init__(self, db_name, osu_client: osu.Client, autofill=True, max_counting_scores=100):
        self.db_name = db_name
        self.client = osu_client
        self.autofill = autofill
        self.max_counting_scores = max_counting_scores

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
                    
                    counting INTEGER NOT NULL CHECK(counting = 0 OR counting = 1) DEFAULT 0,
                    submitted_at TEXT NOT NULL,

                    PRIMARY KEY (user_id, beatmap_id),
                    FOREIGN KEY (user_id) REFERENCES users(osu_id)
                );
            """)

            # score_id is an osu! score's unique identifier.
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_score_id
                ON scores (score_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_beatmap_pp
                ON scores (
                    beatmap_id,
                    pp DESC
                );
            """)

            # Supports finding the current counting score on a map.
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_counting_beatmap_pp
                ON scores (
                    beatmap_id,
                    pp DESC,
                    submitted_at ASC
                )
                WHERE counting = 1;
            """)

            # Supports:
            # - counting a user's counting scores
            # - retrieving their best scores
            # - retrieving their worst counting score
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_counting_pp
                ON scores (
                    user_id,
                    pp DESC,
                    submitted_at ASC
                )
                WHERE counting = 1;
            """)

            # Supports the global leaderboard query.
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_counting_pp
                ON scores (
                    pp DESC,
                    submitted_at ASC
                )
                WHERE counting = 1;
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_all_pp_submission
                ON scores (
                    pp DESC,
                    submitted_at ASC
                );""")


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
                        
                    background BLOB);
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
                return return_str

    def clear_records(self):
        try:
            with sqlite3.connect(self.db_name) as connection:

                cur = connection.cursor()
                cur.execute("DELETE FROM scores;")
                return True
        except sqlite3.Error as error:
            print(f"Could not clear score database: {error}")
            return False

    def add_beatmap_to_beatmap_metadata(self, beatmap_id: int):
        try:
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
        try: 
            with sqlite3.connect(self.db_name) as connection:
                cur = connection.cursor()

                res = cur.execute("""SELECT artist, song_title, difficulty FROM beatmap_meta WHERE beatmap_id = ?""", (beatmap_id,)).fetchone()
                artist, title, version = res[0], res[1], res[2]
                return f"{artist} - {title} [{version}]"

        except sqlite3.IntegrityError as Error:
            print(f"Could not find beatmap_id or  artist, title, or difficulty for the beatmap in the database: {Error}")
            return False

    def score_exists_in_db(self, score_id:int) -> bool:
        try:
            with sqlite3.connect(self.db_name) as connection:
                cur = connection.cursor()

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

    def get_beatmap_max_combo(self, beatmap_id: int) -> int | None:
        try:
            with sqlite3.connect(self.db_name) as connection:
                row = connection.execute(
                    """
                    SELECT max_combo
                    FROM beatmap_meta
                    WHERE beatmap_id = ?;
                    """,
                    (beatmap_id,)
                ).fetchone()

            return None if row is None else row[0]
        except sqlite3.IntegrityError as Error:
            print(f"could not get beatmap max: {Error}")
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
                
            if not self.add_beatmap_to_beatmap_metadata(score_object.beatmap_id):
                print("Failed to add beatmap metadata")
                return False

        username = score_object.user.username
        beatmap_name = self.get_beatmamp_display_name(score_object.beatmap_id)
        beatmap_max_combo = self.get_beatmap_max_combo(score_object.beatmap_id)

        miss_count = score_object.statistics.miss if score_object.statistics.miss is not None else 0
        submitted_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")

        try:
            with sqlite3.connect(self.db_name) as connection:
                connection.execute("PRAGMA foreign_keys = ON;")
                cur = connection.cursor()

                team = cur.execute("""SELECT team FROM users WHERE osu_id = ?""", (score_object.user_id,)) .fetchone()[0]
                
                res = cur.execute("""
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
                        submitted_at,
                        counting
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        team = excluded.team,
                        miss_count = excluded.miss_count,
                        submitted_at = excluded.submitted_at,
                        counting = excluded.counting
                    WHERE scores.pp < excluded.pp
                    RETURNING score_id;     
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
                    submitted_at,
                    0 #counting is automatically set to false, if autofill, will be reset to 1

                )).fetchone()

                if res is None:
                    print("added score was not better")
                    return False
                else:
                    previous_map_score = cur.execute(
                        """
                        SELECT username, user_id, pp, score_id
                        FROM scores
                        WHERE beatmap_id = ?
                        AND counting = 1
                        ORDER BY
                            pp DESC,
                            submitted_at ASC
                        LIMIT 1;
                        """,
                        (score_object.beatmap_id,)
                    ).fetchone()

                    score_counted = self.update_counting_on_beatmap(cur, score_object.beatmap_id, score_object.id, score_object.user_id)

                    if (
                        score_counted
                        and previous_map_score is not None
                        and previous_map_score[1] != score_object.user_id
                        and score_object.pp > previous_map_score[2]
                    ):
                        print(
                            f"{previous_map_score[0]}'s score on "
                            f"{beatmap_name} was sniped by {username}!"
                        )
                    
                    return True

        except sqlite3.IntegrityError as error:
            print(f"Could not add score: {error}")
            return False
            
    def get_recent_score(self, user_id:int, pos=0):
        return self.client.get_user_scores(user_id, osu.UserScoreType.RECENT, include_fails=False, limit=1 + pos)
    
    def get_top_score_on_beatmap(self, beatmap_id:int) -> tuple[str, float, int]:
        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            # NOTE LIMIT 1 IS FOR THE AUTOFILL CONDIITON WHERE EVERYTHING IS COUNTED, FOR NON-AUTO ONLY ONE VALUE SHOULD BE COUNTING
            res = cur.execute("""SELECT username, pp, score_id 
                        FROM scores
                        WHERE beatmap_id = ? AND counting = 1 
                        ORDER BY pp DESC 
                        LIMIT 1""", (beatmap_id,)).fetchone()
            
            if res is None:
                # print(f"No counting score on the beatmap {beatmap_id} currently exists")
                return False
            
            # print(f"The current best score on {beatmap_id} is {res[0]}'s score worth {res[1]}pp!")
            return(res)
    
    
    def calculate_leaderboard_pp(
        self,
        weighting: float,
        max_num_scores: int
    ) -> dict[str, float]:

        with sqlite3.connect(self.db_name) as connection:
            cur = connection.cursor()

            teams = [
                row[0]
                for row in cur.execute(
                    "SELECT DISTINCT team FROM scores;"
                ).fetchall()
            ]

            if self.autofill:
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
                    ORDER BY
                        pp DESC,
                        submitted_at ASC;
                    """
                ).fetchall()
            else:
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
                        submitted_at ASC;
                    """
                ).fetchall()

            claimed_maps = set()
            player_score_counts = defaultdict(int)
            owned_scores = []

            # Phase 1: determine which score owns each map.
            for (
                user_id,
                beatmap_id,
                team,
                pp,
                submitted_at,
                score_id
            ) in rows:

                if beatmap_id in claimed_maps:
                    continue

                if self.autofill:
                    # Non-autofill has already enforced this when assigning
                    # counting values.
                    if (
                        player_score_counts[user_id]
                        >= self.max_counting_scores
                    ):
                        continue

                    player_score_counts[user_id] += 1

                claimed_maps.add(beatmap_id)

                owned_scores.append(
                    (
                        team,
                        pp,
                        beatmap_id,
                        score_id
                    )
                )

            # Phase 2: calculate each team's total from the maps it owns.
            team_scores = {team: 0.0 for team in teams}
            team_score_counts = {team: 0 for team in teams}
            team_weightings = {team: 1.0 for team in teams}

            # owned_scores remains globally ordered by PP because rows was
            # globally ordered.
            for team, pp, beatmap_id, score_id in owned_scores:
                # The team still owns and blocks this map even when the
                # score does not fit into its scoring limit.
                if team_score_counts[team] >= max_num_scores:
                    continue

                team_scores[team] += pp * team_weightings[team]
                team_score_counts[team] += 1
                team_weightings[team] *= weighting

            for team, total_pp in team_scores.items():
                print(f"team {team}: {total_pp}pp")

            return team_scores

    def update_counting_on_beatmap(self, cur: sqlite3.Cursor, beatmap_id: int, score_id: int, user_id: int) -> bool:
        if self.autofill:
            cur.execute(
                """
                UPDATE scores
                SET counting = 1
                WHERE score_id = ?;
                """,
                (score_id,)
            )
            return True

        # Get the submitted score's PP.
        added_score_row = cur.execute(
            """
            SELECT pp
            FROM scores
            WHERE score_id = ?;
            """,
            (score_id,)
        ).fetchone()

        if added_score_row is None:
            print(f"Could not find submitted score {score_id}")
            return False

        added_score_pp = added_score_row[0]

        map_counting_score = cur.execute(
            """
            SELECT score_id, user_id, pp
            FROM scores
            WHERE beatmap_id = ?
            AND counting = 1
            LIMIT 1;
            """,
            (beatmap_id,)
        ).fetchone()

        if map_counting_score is not None:
            map_counting_id, map_counting_user_id, map_counting_pp = (map_counting_score)

            if added_score_pp <= map_counting_pp:
                return False
            
        else:
            map_counting_id = None

        # Count the player's currently counting scores.
        player_counting_count = cur.execute(
            """
            SELECT COUNT(*)
            FROM scores
            WHERE user_id = ?
            AND counting = 1;
            """,
            (user_id,)
        ).fetchone()[0]

        worst_counting_id = None

        if player_counting_count >= self.max_counting_scores:
            worst_counting_score = cur.execute(
                """
                SELECT score_id, pp
                FROM scores
                WHERE user_id = ?
                AND counting = 1
                ORDER BY
                    pp ASC,
                    submitted_at DESC
                LIMIT 1;
                """,
                (user_id,)
            ).fetchone()

            if worst_counting_score is None:
                print("Could not find player's lowest counting score.")
                return False

            worst_counting_id, worst_counting_pp = worst_counting_score

            # Existing score wins a PP tie because it was submitted first.
            if added_score_pp <= worst_counting_pp:
                print(
                    "Player's existing counting scores are at least as good; "
                    "new score will not count."
                )
                return False

        # At this point, the score passes both requirements:
        # 1. It beats the current counting score on the map, if one exists.
        # 2. It is good enough to enter the player's counting scores.

        # Disable the previous map winner before enabling the new one.
        if map_counting_id is not None:
            cur.execute(
                """
                UPDATE scores
                SET counting = 0
                WHERE score_id = ?;
                """,
                (map_counting_id,)
            )

        cur.execute(
            """
            UPDATE scores
            SET counting = 1
            WHERE score_id = ?;
            """,
            (score_id,)
        )

        # If the player was already at their limit, remove their previous
        # lowest counting score. That score's map remains empty.
        if worst_counting_id is not None:
            cur.execute(
                """
                UPDATE scores
                SET counting = 0
                WHERE score_id = ?;
                """,
                (worst_counting_id,)
            )

        return True

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

    db = OsuScoreDB("mmosu.db", osu_client,False, 10)
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
        max_num_scores=10,
    )
