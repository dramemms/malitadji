import json

INPUT = "export_stations_utf8.json"
OUTPUT = "localisation_only.json"

keep = {"stations.region", "stations.cercle", "stations.commune"}

with open(INPUT, "r", encoding="utf-8-sig") as f:
    data = json.load(f)

filtered = [o for o in data if o.get("model") in keep]

with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

print(f"OK: {len(filtered)} objets -> {OUTPUT}")
