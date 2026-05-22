import redis    
import json

r = redis.Redis(host = "localhost", port = "6379", db = 0)
pubsub = r.pubsub()
pubsub.subscribe("new_book")

print("listeninf for new book")

for message in pubsub.listen():
    if message["type"] == "message":
        data = json.loads(message["data"])
        print(f"New book added by {data['user']}: {data['title']} by {data['author']}")