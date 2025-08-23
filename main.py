from flask import Flask, jsonify, render_template_string
import json
import urllib.parse

enc = "cp932"
path = "new_data/pft.csv"

print("hello rath")

try:
    with open(path, encoding="utf-8-sig") as f:
        lines = f.readlines()
    print("Decoded with utf-8-sig")
except UnicodeDecodeError:
    with open(path, encoding="cp932", errors="replace") as f:
        lines = f.readlines()
    print("Decoded with cp932 (with replacements)")
print(f"Decoded with {enc}")

lines = [x.strip() for x in lines]
lines = [x.split(",") for x in lines]

# Build structured park list (name, address, lat, lon, desc/url if present)
parks = []
raw_categories = []
for row in lines:
    if len(row) < 53:
        continue

    # Extract all row-derived variables at the top
    name = row[3].strip()
    address = row[12].strip()
    lat_raw = row[18].strip()
    lon_raw = row[19].strip()
    url = row[52].strip()
    desc = row[34].strip()
    category = row[-1].strip() if row[-1] else "その他"  # last column treated as category per user instruction

    if not lat_raw or not lon_raw:
        continue
    try:
        lat = float(lat_raw)
        lon = float(lon_raw)
    except ValueError:
        continue

    raw_categories.append(category)
    parks.append({
        "name": name,
        "address": address,
        "lat": lat,
        "lon": lon,
        "url": url,
        "desc": desc,
        "category": category,
    })

# Build deterministic color palette for categories (internal symbolic names)
palette = [
    "red","blue","green","purple","orange","darkred","cadetblue","darkgreen","darkpurple","pink",
    "lightblue","lightgreen","gray","black","lightgray","beige","lightred","darkblue","white"
]
distinct_categories = sorted({c for c in raw_categories if c})
category_colors = {}
for idx, cat in enumerate(distinct_categories):
    category_colors[cat] = palette[idx % len(palette)]

# Mapping of Leaflet marker color names (and custom) to hex for consistent circle styling
color_name_to_hex = {
    'red':'#d63e2a','blue':'#2a81cb','green':'#2aad27','purple':'#6f42c1','orange':'#f69730','darkred':'#772015',
    'cadetblue':'#3c8dbc','darkgreen':'#115f0a','darkpurple':'#301934','pink':'#ff4da3','lightblue':'#87ceeb',
    'lightgreen':'#90ee90','gray':'#808080','black':'#000000','lightgray':'#d3d3d3','beige':'#f5f5dc','lightred':'#ff7f7f',
    'darkblue':'#0a3172','white':'#ffffff'
}

# Attach color to each park and compute hex fallback
for p in parks:
    name_color = category_colors.get(p.get("category"), "blue")
    p["color"] = name_color
    p["hex_color"] = color_name_to_hex.get(name_color, name_color)

# Provide simple center coordinates (Tokyo) for template
center_lat = 35.681236
center_lon = 139.767125

app = Flask(__name__)

# Load template from external file
import os
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template.html")
with open(TEMPLATE_PATH, encoding="utf-8") as f:
    TEMPLATE = f.read()


@app.route("/")
def index():
    # Provide hex color mapping for template
    category_colors_hex = {cat: color_name_to_hex.get(col, col) for cat, col in category_colors.items()}
    payload = {
        "parks": parks,
        "centerLat": center_lat,
        "centerLon": center_lon,
        "categoryColors": category_colors_hex
    }
    json_payload = urllib.parse.quote(json.dumps(payload, ensure_ascii=False))
    templ = TEMPLATE.replace('BOOTSTRAP_JSON_PLACEHOLDER', json_payload)
    return render_template_string(templ)

@app.route("/api/parks")
def api_parks():
    return jsonify(parks)

if __name__ == "__main__":
    app.run(debug=True)
