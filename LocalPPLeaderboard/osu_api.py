from osu import Client
from dotenv import find_dotenv, load_dotenv
import os

## Grabbing Environment Variables
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

client_id = int(os.environ["client_id"])
client_secret = os.environ["client_secret"]
redirect_uri = "http://127.0.0.1:8080"

client = Client.from_credentials(client_id, client_secret, redirect_uri)

events = client.get_user_recent_activity(14715160, limit=100)
print(f"Number of events fetched: {len(events)}")
# print("List of achievement events:")
# print(list(filter(lambda e: isinstance(e, AchievementEvent), events)))
