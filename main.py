from flask import Flask, jsonify, render_template_string, request
import json
import urllib.parse

enc = "cp932"
path = "new_data/pft.csv"

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
    category = row[-1].strip() if row[-1] else "その他" 

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

# Simple bilingual (Japanese/English) translation resources
# Keys correspond to data-i18n attributes in template.
i18n = {
    "ja": {
        "pageTitle": "Tokyo Parks Map | 都立公園マップ",
        "headerTitle": "Tokyo Parks Map | 都立公園マップ",
        "subtitle": "東京の公園を検索・発見できるインタラクティブマップ",
        "searchHeading": "公園を検索",
        "searchPlaceholder": "公園名で検索...",
        "categoriesLabel": "カテゴリー",
        "useLocationLabel": "現在地",
        "selectAll_allSelected": "全解除",
        "selectAll_noneSelected": "全選択",
        "selectAll_partial": "一部",
        "legendTitle": "カテゴリー",
        "aboutHeading": "このサイトについて",
        "aboutParagraph1": "Tokyo Parks Map は東京都内の公園オープンデータを活用し、公園の場所や情報を探しやすくしたウェブアプリです。名前で検索したり、地図上で位置を確認したり、基本的な詳細を見ることができます。",
        "bullet1": "日本語の名称で公園を検索",
        "bullet2": "公園をクリックするとその位置へズーム",
        "bullet3": "住所やリンク（あれば）を確認",
        "bullet4": "東京都オープンデータを利用",
        "bullet5": "Python / Flask / Leaflet.js で構築",
        "footer": "© 2025 Tokyo Parks Map | オープンデータハッカソン"
    },
    "en": {
        "pageTitle": "Tokyo Parks Map | Metropolitan Park Explorer",
        "headerTitle": "Tokyo Parks Map | Metropolitan Park Explorer",
        "subtitle": "Discover, search, and explore Tokyo's public parks on an interactive map.",
        "searchHeading": "Search Parks",
        "searchPlaceholder": "Search by park name...",
        "categoriesLabel": "Categories",
        "useLocationLabel": "Location",
        "selectAll_allSelected": "Deselect All",
        "selectAll_noneSelected": "Select All",
        "selectAll_partial": "Some",
        "legendTitle": "Categories",
        "aboutHeading": "About This Website",
        "aboutParagraph1": "Tokyo Parks Map is an open data web application that helps you discover and explore public parks across Tokyo. The interactive map lets you search by name, zoom to locations, and view basic details. Built for the Open Data Hackathon to promote civic use of public datasets.",
        "bullet1": "Search parks by name (Japanese)",
        "bullet2": "Click a park to zoom to its location",
        "bullet3": "View addresses, links (where available)",
        "bullet4": "Data sourced from Tokyo open government datasets",
        "bullet5": "Built with Python, Flask & Leaflet.js",
        "footer": "© 2025 Tokyo Parks Map | Open Data Hackathon"
    }
}


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
    i18n_payload = urllib.parse.quote(json.dumps(i18n, ensure_ascii=False))
    templ = TEMPLATE.replace('BOOTSTRAP_JSON_PLACEHOLDER', json_payload)
    templ = templ.replace('I18N_JSON_PLACEHOLDER', i18n_payload)
    return render_template_string(templ)

@app.route("/api/parks")
def api_parks():
    return jsonify(parks)

if __name__ == "__main__":
    app.run(debug=True)
