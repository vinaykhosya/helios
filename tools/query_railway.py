import urllib.request
import json

token = "65131ef4-00db-404b-b825-46de76c052cd"
url = "https://backboard.railway.app/graphql/v2"

query = {
    "query": "query { projects { edges { node { id name } } } }"
}

req = urllib.request.Request(
    url,
    data=json.dumps(query).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
)

try:
    with urllib.request.urlopen(req) as resp:
        print("Railway GraphQL API Success:")
        print(resp.read().decode("utf-8"))
except Exception as e:
    print(f"Railway GraphQL Error: {e}")
