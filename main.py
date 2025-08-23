from flask import Flask, jsonify, render_template_string
import folium

enc = "cp932"

try:
    with open("data/c.csv", encoding="utf-8-sig") as f:
        lines = f.readlines()
    print("Decoded with utf-8-sig")
except UnicodeDecodeError:
    with open("data/c.csv", encoding="cp932", errors="replace") as f:
        lines = f.readlines()
    print("Decoded with cp932 (with replacements)")
print(f"Decoded with {enc}")

lines = [x.strip() for x in lines]
lines = [x.split(",") for x in lines]

# Build structured park list (name, address, lat, lon, desc/url if present)
parks = []
for row in lines:
    if len(row) < 12:
        continue
    name = row[4].strip()
    lat_raw = row[10].strip()
    lon_raw = row[11].strip()
    if not lat_raw or not lon_raw:
        continue
    try:
        lat = float(lat_raw)
        lon = float(lon_raw)
    except ValueError:
        continue
    # Fix obviously swapped coordinates (latitude should be between -90..90)
    if abs(lat) > 90 and abs(lon) <= 90:
        lat, lon = lon, lat
    if abs(lat) > 90 or abs(lon) > 180:
        continue
    address = row[8].strip()
    url = ""
    # Try to find a URL in the row
    for c in row:
        if c.startswith("http://") or c.startswith("https://"):
            url = c
            break
    desc = ""
    # Grab a long-ish Japanese description field (heuristic: length > 40, not URL)
    for c in row:
        if len(c) > 40 and "http" not in c and all(x not in c for x in ['〒']):
            desc = c.replace('"', '').strip()
            break
    parks.append({
        "name": name,
        "address": address,
        "lat": lat,
        "lon": lon,
        "url": url,
        "desc": desc
    })

# Center map (Tokyo)
center_lat = 35.681236
center_lon = 139.767125

m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")
for p in parks:
    popup_html = f"<b>{p['name']}</b><br>{p['address']}<br>"
    if p['url']:
        popup_html += f"<a href='{p['url']}' target='_blank'>Link</a><br>"
    if p['desc']:
        popup_html += f"<small>{p['desc'][:180]}...</small>"
    folium.Marker(
        [p['lat'], p['lon']],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=p['name']
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
