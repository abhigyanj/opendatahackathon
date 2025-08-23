from flask import Flask, jsonify, render_template_string
import folium

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
    category = row[-1].strip() if row[-1] else ""  # last column treated as category per user instruction

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

# Build deterministic color palette for categories
palette = [
    "red","blue","green","purple","orange","darkred","cadetblue","darkgreen","darkpurple","pink",
    "lightblue","lightgreen","gray","black","lightgray","beige","lightred","darkblue","white"
]
distinct_categories = sorted({c for c in raw_categories if c})
category_colors = {}
for idx, cat in enumerate(distinct_categories):
    category_colors[cat] = palette[idx % len(palette)]

# Attach color to each park (fallback color if missing)
for p in parks:
    p["color"] = category_colors.get(p.get("category"), "blue")

# Center map (Tokyo)
center_lat = 35.681236
center_lon = 139.767125

m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")
for p in parks:
    popup_html = f"<b>{p['name']}</b><br>{p['address']}<br>"
    if p['category']:
        popup_html += f"<span style='display:inline-block;padding:2px 6px;background:#eee;border-radius:4px;font-size:11px;margin:2px 0;'>{p['category']}</span><br>"
    if p['url']:
        popup_html += f"<a href='{p['url']}' target='_blank'>Link</a><br>"
    if p['desc']:
        popup_html += f"<small>{p['desc'][:180]}...</small>"
    # Use colored icon based on category color
    icon = folium.Icon(color=p['color'], icon="info-sign")
    folium.Marker(
        [p['lat'], p['lon']],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=p['name'],
        icon=icon
    ).add_to(m)

map_html = m._repr_html_()

# Inject map reference for sidebar functionality
map_html = map_html.replace('</script>', '''
    // Expose map object for sidebar clicks
    window.leafletMapObj = eval(Object.keys(window).find(k => k.startsWith('map_') && window[k] && window[k].setView));
</script>''')

app = Flask(__name__)

# Load template from external file
import os
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template.html")
with open(TEMPLATE_PATH, encoding="utf-8") as f:
    TEMPLATE = f.read()


@app.route("/")
def index():
    return render_template_string(TEMPLATE, map_html=map_html, parks_json=parks)

@app.route("/api/parks")
def api_parks():
    return jsonify(parks)

if __name__ == "__main__":
    app.run(debug=True)
