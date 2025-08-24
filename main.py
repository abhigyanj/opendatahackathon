from flask import Flask, jsonify, render_template_string, request
import json
import urllib.parse

enc = "cp932"
path = "public_facilities_merged_all_recategorized_full_v9.csv"

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
public_facilities = []
raw_categories = []

for row in lines:
    # Extract all row-derived variables at the top
    name = row[0].strip()
    address = row[1].strip()
    lat_raw = row[3].strip()
    lon_raw = row[4].strip()
    url = row[2].strip()
    category = row[6].strip() if row[-1] else "その他" 

    # print(name, address, lat_raw, lon_raw, url, category)

    if not lat_raw or not lon_raw:
        continue
    try:
        lat = float(lat_raw)
        lon = float(lon_raw)
    except ValueError:
        continue

    raw_categories.append(category)
    public_facilities.append({
        "name": name,
        "address": address,
        "lat": lat,
        "lon": lon,
        "url": url,
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
for p in public_facilities:
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

I18N_PATH = os.path.join(os.path.dirname(__file__), "i18n.json")
with open(I18N_PATH, encoding="utf-8") as f:
    i18n = json.load(f)


@app.route("/")
def index():
    # Provide hex color mapping for template
    category_colors_hex = {cat: color_name_to_hex.get(col, col) for cat, col in category_colors.items()}
    payload = {
        "publicFacilities": public_facilities,
        "centerLat": center_lat,
        "centerLon": center_lon,
        "categoryColors": category_colors_hex
    }
    json_payload = urllib.parse.quote(json.dumps(payload, ensure_ascii=False))
    i18n_payload = urllib.parse.quote(json.dumps(i18n, ensure_ascii=False))
    templ = TEMPLATE.replace('BOOTSTRAP_JSON_PLACEHOLDER', json_payload)
    templ = templ.replace('I18N_JSON_PLACEHOLDER', i18n_payload)
    return render_template_string(templ)

@app.route("/api/facilities")
def api_facilities():
    return jsonify(public_facilities)

if __name__ == "__main__":
    app.run(debug=True)
