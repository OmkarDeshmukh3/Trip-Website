from pathlib import Path
import csv
import json
import math
import os
import re
import sqlite3
from datetime import date, timedelta
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen
import threading
import time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, BASE_DIR
from recommendation_engine import recommend_destinations

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-tripgenie-development-key-change-before-deploying")

# Best-effort geocoding cache. The public Nominatim service is rate-limited to
# one request/second; cache hits don't make a network request. For public scale,
# configure a dedicated geocoding provider instead of relying on the public demo.
_GEOCODE_CACHE = {}
_GEOCODE_LOCK = threading.Lock()
_GEOCODE_LAST_REQUEST = 0.0

# Curated Maharashtra Engineering Marvels & Natural Wonders.
# Coordinates are location markers for discovery and map animation, not survey-grade navigation data.
MARVELS = [
    {"id":"ajanta", "name":"Ajanta Caves", "kind":"Ancient rock-cut art", "lat":20.55311, "lon":75.70025, "zoom":14,
     "description":"Buddhist cave monuments with remarkable murals, sculptures and monastery spaces carved into a cliff.",
     "why":"Explore how ancient builders shaped halls, shrines and living spaces directly into the rock.",
     "image":"https://www.ancient-origins.de/sites/default/files/field/image/ajanta-hoehlen.jpg",
     "source":"https://whc.unesco.org/en/list/242/", "source_label":"UNESCO · Ajanta Caves", "travel_name":"Ajanta Caves"},
    {"id":"ellora", "name":"Ellora Caves (Verul)", "kind":"Rock-cut complex", "lat":20.02639, "lon":75.17917, "zoom":14,
     "description":"A vast sequence of Buddhist, Hindu and Jain monuments excavated from a basalt cliff.",
     "why":"See how different religious traditions and generations shaped one extraordinary cave complex.",
     "image":"https://portfolio.investmentguruindia.com/uploads/news/cultural%20tourism_12042026.jpg",
     "source":"https://whc.unesco.org/en/list/243/", "source_label":"UNESCO · Ellora Caves", "travel_name":"Ellora Caves"},
    {"id":"kailasa", "name":"Kailasa Temple · Cave 16", "kind":"Monolithic engineering", "lat":20.02380, "lon":75.17720, "zoom":17,
     "description":"The celebrated Ellora temple excavated from a single mass of basalt, with a monumental courtyard and detailed sculpture.",
     "why":"A powerful case study in rock removal, structural planning, symmetry, sculpture and scale.",
     "image":"https://portfolio.investmentguruindia.com/uploads/news/cultural%20tourism_12042026.jpg",
     "source":"https://whc.unesco.org/en/list/243/", "source_label":"UNESCO · Ellora / Cave 16", "travel_name":"Kailasa Temple"},
    {"id":"lonar", "name":"Lonar Impact Crater", "kind":"Geological wonder", "lat":19.97640, "lon":76.50930, "zoom":13,
     "description":"A near-circular crater in Deccan basalt that filled with a saline-alkaline lake after a meteorite impact.",
     "why":"Study impact geology, basalt, crater formation and a rare lake ecosystem. The crater is the impact site—not the meteorite itself.",
     "image":"https://assets.science.nasa.gov/dynamicimage/assets/science/esd/eo/images/imagerecords/146000/146859/lonarlake_oli_2020162_lrg.jpg?crop=faces%2Cfocalpoint&fit=clip&h=1145&w=1209",
     "source":"https://maharashtratourism.gov.in/nature/lonar-crater/", "source_label":"Maharashtra Tourism · Lonar Crater", "travel_name":"Lonar Crater"},
    {"id":"karla", "name":"Karla Caves", "kind":"Ancient cave engineering", "lat":18.78210, "lon":73.47120, "zoom":15,
     "description":"Buddhist rock-cut caves near Lonavala, known for a large chaitya hall with a vaulted ceiling and pillars.",
     "why":"Notice the carved hall, column rhythm, roof form and engineering of a space cut into living rock.",
     "image":"https://assets.simplotel.com/simplotel/image/upload/x_0%2Cy_100%2Cw_1920%2Ch_1080%2Cr_0%2Cc_crop/q_80%2Cw_455%2Cdpr_1%2Cf_auto%2Cfl_progressive%2Cc_limit/athiva-hotels-resorts/karla-caves",
     "source":"https://maharashtratourism.gov.in/", "source_label":"Maharashtra Tourism", "travel_name":"Karla Caves"},
    {"id":"daulatabad", "name":"Daulatabad Fort", "kind":"Defensive engineering", "lat":19.94280, "lon":75.21610, "zoom":14,
     "description":"A hill fortress known for its strategic topography and layered defensive approach.",
     "why":"Look at how terrain, access paths and defensive design work together. Check current site conditions before visiting.",
     "image":"https://images.unsplash.com/photo-1606293926075-69a00dbfde81?auto=format&fit=crop&w=1200&q=85",
     "source":"https://maharashtratourism.gov.in/districts/chhattrapati-sambhaji-nagar/", "source_label":"Maharashtra Tourism · Forts", "travel_name":"Daulatabad Fort"},
    {"id":"elephanta", "name":"Elephanta Caves", "kind":"Rock-cut temple art", "lat":18.96330, "lon":72.93150, "zoom":15,
     "description":"An island cave complex known for monumental stone sculpture and Shaivite iconography near Mumbai.",
     "why":"Explore how sculptors shaped large figures, sanctuaries and ceremonial space from living rock.",
     "image":"https://images.unsplash.com/photo-1606293926075-69a00dbfde81?auto=format&fit=crop&w=1200&q=85",
     "source":"https://whc.unesco.org/en/list/244/", "source_label":"UNESCO · Elephanta Caves", "travel_name":"Elephanta Caves"},
    {"id":"pandavleni", "name":"Pandavleni Caves", "kind":"Ancient Buddhist caves", "lat":20.00980, "lon":73.73930, "zoom":15,
     "description":"A group of ancient Buddhist caves carved into a hill overlooking Nashik.",
     "why":"Notice the rock-cut rooms, inscriptions, water systems and placement along the hillside.",
     "image":"https://images.unsplash.com/photo-1606293926075-69a00dbfde81?auto=format&fit=crop&w=1200&q=85",
     "source":"https://maharashtratourism.gov.in/", "source_label":"Maharashtra Tourism", "travel_name":"Pandavleni Caves"},
    {"id":"raigad", "name":"Raigad Fort", "kind":"Capital-fort engineering", "lat":18.23320, "lon":73.44020, "zoom":14,
     "description":"A hill fort strongly associated with Maratha history, with monumental approaches and remains on a high plateau.",
     "why":"Study how a difficult-to-access hilltop could support defence, administration and a historic capital.",
     "image":"https://images.unsplash.com/photo-1606293926075-69a00dbfde81?auto=format&fit=crop&w=1200&q=85",
     "source":"https://maharashtratourism.gov.in/", "source_label":"Maharashtra Tourism", "travel_name":"Raigad Fort"},
    {"id":"pratapgad", "name":"Pratapgad Fort", "kind":"Hill-fort defence", "lat":17.93600, "lon":73.58000, "zoom":14,
     "description":"A historic fort on a Sahyadri ridge near Mahabaleshwar, shaped by steep terrain and defensive walls.",
     "why":"Consider the role of elevation, slopes and controlled approaches in fort architecture.",
     "image":"https://images.unsplash.com/photo-1606293926075-69a00dbfde81?auto=format&fit=crop&w=1200&q=85",
     "source":"https://maharashtratourism.gov.in/", "source_label":"Maharashtra Tourism", "travel_name":"Pratapgad Fort"},
    {"id":"panhala", "name":"Panhala Fort", "kind":"Fortification and water systems", "lat":16.81150, "lon":74.10700, "zoom":14,
     "description":"A large hill fort near Kolhapur known for extensive defensive works and historical structures.",
     "why":"Explore the scale of the fort, its gates, walls, strategic terrain and historic water-management features.",
     "image":"https://images.unsplash.com/photo-1606293926075-69a00dbfde81?auto=format&fit=crop&w=1200&q=85",
     "source":"https://maharashtratourism.gov.in/", "source_label":"Maharashtra Tourism", "travel_name":"Panhala Fort"},
]



def csv_rows(filename):
    path = BASE_DIR / "data" / filename
    with path.open(newline="", encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def ensure_column(cursor, table, name, sql_type):
    columns = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()}
    if name not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")


def create_database():
    """Create/migrate the local SQLite schema and sync sample records from CSV."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS destinations (
        destination_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, location TEXT, description TEXT, category TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS hotels (
        hotel_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, location TEXT, price INTEGER, rating REAL)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS places (
        place_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, location TEXT, category TEXT, description TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, place_id INTEGER, rating INTEGER, comment TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS recommendation_feedback (
        feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        destination_name TEXT NOT NULL,
        signal INTEGER NOT NULL CHECK(signal IN (-1, 1)),
        interest TEXT,
        travel_date TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id))""")

    for name, sql_type in [
        ("latitude", "REAL"), ("longitude", "REAL"), ("budget_per_day", "INTEGER"),
        ("ideal_days", "INTEGER"), ("interests", "TEXT"), ("image_url", "TEXT")]:
        ensure_column(cursor, "destinations", name, sql_type)
    for name, sql_type in [("latitude", "REAL"), ("longitude", "REAL"), ("area", "TEXT"), ("description", "TEXT")]:
        ensure_column(cursor, "hotels", name, sql_type)
    for name, sql_type in [("latitude", "REAL"), ("longitude", "REAL")]:
        ensure_column(cursor, "places", name, sql_type)
    connection.commit()
    connection.close()
    seed_database_from_csv()


def seed_database_from_csv():
    """The editable CSV files are the source for destination/place/hotel demo data."""
    connection = get_connection()
    cursor = connection.cursor()
    # Remove fabricated prototype hotel entries. TripGenie now links to real,
    # current accommodation search results instead of showing made-up properties.
    cursor.execute("DELETE FROM hotels WHERE name IN (?, ?, ?, ?) OR name LIKE ?",
                   ("Hotel Pune", "Goa Beach Hotel", "Jaipur Palace Hotel", "Manali Hill Hotel", "TripGenie Demo Stay%"))
    for row in csv_rows("destinations.csv"):
        values = (row["name"], row["state"], row["description"], row["category"],
                  float(row["latitude"]), float(row["longitude"]), int(row["budget_per_day"]),
                  int(row["ideal_days"]), row["interests"], row["image_url"])
        existing = cursor.execute("SELECT destination_id FROM destinations WHERE name = ?", (row["name"],)).fetchone()
        if existing:
            cursor.execute("""UPDATE destinations SET location=?, description=?, category=?, latitude=?, longitude=?,
                budget_per_day=?, ideal_days=?, interests=?, image_url=? WHERE destination_id=?""",
                (*values[1:], existing["destination_id"]))
        else:
            cursor.execute("""INSERT INTO destinations
                (name,location,description,category,latitude,longitude,budget_per_day,ideal_days,interests,image_url)
                VALUES (?,?,?,?,?,?,?,?,?,?)""", values)

    for row in csv_rows("places.csv"):
        values = (row["name"], row["location"], row["category"], row["description"], float(row["latitude"]), float(row["longitude"]))
        existing = cursor.execute("SELECT place_id FROM places WHERE name = ? AND location = ?", (row["name"], row["location"])).fetchone()
        if existing:
            cursor.execute("UPDATE places SET category=?, description=?, latitude=?, longitude=? WHERE place_id=?",
                           (row["category"], row["description"], float(row["latitude"]), float(row["longitude"]), existing["place_id"]))
        else:
            cursor.execute("""INSERT INTO places (name,location,category,description,latitude,longitude)
                VALUES (?,?,?,?,?,?)""", values)

    for row in csv_rows("hotels.csv"):
        values = (row["name"], row["location"], int(row["price"]), float(row["rating"]),
                  float(row["latitude"]), float(row["longitude"]), row["area"], row["description"])
        existing = cursor.execute("SELECT hotel_id FROM hotels WHERE name = ? AND location = ?", (row["name"], row["location"])).fetchone()
        if existing:
            cursor.execute("""UPDATE hotels SET price=?, rating=?, latitude=?, longitude=?, area=?, description=? WHERE hotel_id=?""",
                           (int(row["price"]), float(row["rating"]), float(row["latitude"]), float(row["longitude"]), row["area"], row["description"], existing["hotel_id"]))
        else:
            cursor.execute("""INSERT INTO hotels (name,location,price,rating,latitude,longitude,area,description)
                VALUES (?,?,?,?,?,?,?,?)""", values)

    # The CSV catalogue is the source of truth. This keeps outdated demo rows
    # from an older TripGenie database from reappearing beside the new catalogue.
    valid_destinations = {row["name"] for row in csv_rows("destinations.csv")}
    for old in cursor.execute("SELECT destination_id, name FROM destinations").fetchall():
        if old["name"] not in valid_destinations:
            cursor.execute("DELETE FROM destinations WHERE destination_id=?", (old["destination_id"],))

    valid_place_pairs = {(row["name"], row["location"]) for row in csv_rows("places.csv")}
    for old in cursor.execute("SELECT place_id, name, location FROM places").fetchall():
        if (old["name"], old["location"]) not in valid_place_pairs:
            cursor.execute("DELETE FROM places WHERE place_id=?", (old["place_id"],))

    connection.commit()
    connection.close()


def all_destinations():
    connection = get_connection()
    rows = [dict(row) for row in connection.execute("SELECT * FROM destinations ORDER BY name").fetchall()]
    connection.close()
    return rows


def destination_map():
    return {item["name"]: item for item in all_destinations()}


def _is_site_destination(item):
    """Exclude individual landmarks from the starting-city picker."""
    name = str(item.get("name", "")).casefold()
    category = str(item.get("category", "")).casefold()
    # Keep regional hubs available as origins even if their broad category is coastal.
    if name in {"goa", "puducherry", "port blair (sri vijaya puram)", "lakshadweep agatti island"}:
        return False
    site_categories = {"fort", "beach", "engineering marvel", "natural wonder", "wildlife", "waterfall", "island", "monument", "national park"}
    if category in site_categories:
        return True
    site_terms = (" fort", "fort ", " beach", " caves", " cave", " temple", " crater", " waterfall", " waterfalls",
                  " national park", " tiger reserve", "stupa", "tso", "island", "sun temple", "stupa", "plateau")
    return any(term in name for term in site_terms) or name.endswith(("fort", "beach", "caves", "cave", "crater", "waterfall", "stupa"))


@app.route("/explore")
def explore():
    all_items = all_destinations()
    query = request.args.get("q", "").strip().casefold()
    category = request.args.get("category", "All").strip()
    category_map = {
        "Forts": {"fort"}, "Beaches": {"beach"}, "Heritage & caves": {"heritage", "engineering marvel", "historical"},
        "Nature & hills": {"nature", "hill station", "natural wonder", "lake", "mountain", "adventure", "waterfall"},
        "Spiritual": {"spiritual"}, "Wildlife": {"wildlife", "national park"}, "Cities": {"city", "coastal town", "food & heritage", "culture"}
    }
    filtered = []
    for item in all_items:
        if query and query not in " ".join(str(item.get(k, "")) for k in ("name", "location", "description", "category", "interests")).casefold():
            continue
        if category in category_map and item.get("category", "").casefold() not in category_map[category]:
            tags = str(item.get("interests", "")).casefold()
            if category == "Forts" and "forts" not in tags: continue
            if category == "Beaches" and "beach" not in tags: continue
            if category == "Heritage & caves" and not any(t in tags for t in ("historical", "engineering marvel", "culture")): continue
            if category == "Nature & hills" and not any(t in tags for t in ("nature", "natural wonders", "adventure")): continue
            if category == "Spiritual" and "spiritual" not in tags: continue
            if category == "Wildlife" and not any(t in tags for t in ("wildlife", "zoo")): continue
            if category == "Cities" and _is_site_destination(item): continue
        filtered.append(item)
    return render_template("explore.html", destinations=filtered, query=request.args.get("q", ""), category=category,
                           total_count=len(all_items))


@app.route("/api/geocode")
def api_geocode():
    """Best-effort exact pin lookup for known catalog sites, cached and rate-limited."""
    global _GEOCODE_LAST_REQUEST
    name = request.args.get("name", "").strip()
    context = request.args.get("context", "").strip()
    if not name or len(name) > 140 or len(context) > 140:
        return jsonify(found=False, reason="invalid query"), 400
    known_names = {item["name"].casefold() for item in all_destinations()}
    connection = get_connection()
    try:
        row = connection.execute("SELECT 1 FROM places WHERE lower(name)=lower(?) LIMIT 1", (name,)).fetchone()
    finally:
        connection.close()
    if name.casefold() not in known_names and not row and not any(name.casefold() == x["name"].casefold() for x in MARVELS):
        return jsonify(found=False, reason="site is not in the TripGenie catalogue"), 404
    cache_key = (name.casefold(), context.casefold())
    with _GEOCODE_LOCK:
        cached = _GEOCODE_CACHE.get(cache_key)
        if cached and time.time() - cached[0] < 86400:
            return jsonify(cached[1])
        delay = 1.05 - (time.monotonic() - _GEOCODE_LAST_REQUEST)
        if delay > 0:
            time.sleep(delay)
        _GEOCODE_LAST_REQUEST = time.monotonic()
    query = ", ".join(part for part in (name, context, "India") if part)
    url = "https://nominatim.openstreetmap.org/search?" + urlencode({"q": query, "format": "jsonv2", "limit": 1, "addressdetails": 1})
    result = {"found": False}
    try:
        req = Request(url, headers={"User-Agent": "TripGenieCollegePrototype/1.0 (educational travel-planning demo)"})
        with urlopen(req, timeout=3.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload:
            item = payload[0]
            lat, lon = float(item["lat"]), float(item["lon"])
            display = str(item.get("display_name", ""))
            name_hint = str(item.get("name", ""))
            # Don't accept an unrelated broad hit; the curated coordinates remain fallback.
            terms = [t for t in re.findall(r"[a-z0-9]+", name.casefold()) if len(t) > 2]
            haystack = (name_hint + " " + display).casefold()
            matches = sum(1 for term in terms if term in haystack)
            if terms and matches / len(terms) >= 0.5 and 5 <= lat <= 38 and 65 <= lon <= 100:
                result = {"found": True, "lat": lat, "lon": lon, "label": display, "source": "OpenStreetMap Nominatim"}
    except Exception:
        result = {"found": False, "reason": "geocoding unavailable; curated fallback coordinates used"}
    with _GEOCODE_LOCK:
        _GEOCODE_CACHE[cache_key] = (time.time(), result)
    return jsonify(result)


@app.route("/")
def home():
    destinations = all_destinations()
    featured_names = ["Mahabaleshwar", "Lonavala", "Lonar Crater", "Ajanta Caves", "Ellora Caves", "Nagpur"]
    by_name = {item["name"]: item for item in destinations}
    featured = [by_name[name] for name in featured_names if name in by_name]
    return render_template("index.html", featured=featured, destination_count=len(destinations), featured_marvels=[MARVELS[0], MARVELS[2], MARVELS[3]])



@app.route("/marvels")
def marvels():
    """Interactive discovery page for engineering and geological wonders."""
    return render_template("marvels.html", marvels=MARVELS)


@app.route("/wildlife")
def wildlife():
    """Browse zoological parks in the curated Maharashtra sample dataset."""
    connection = get_connection()
    zoos = [dict(row) for row in connection.execute(
        "SELECT * FROM places WHERE category = ? ORDER BY location, name", ("Zoo & Wildlife",)
    ).fetchall()]
    connection.close()
    return render_template("wildlife.html", zoos=zoos)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            error = "Enter your name, a valid email, and a password with at least 6 characters."
        else:
            connection = get_connection()
            try:
                connection.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
                                   (name, email, generate_password_hash(password)))
                connection.commit()
            except sqlite3.IntegrityError:
                error = "That email is already registered. Try logging in."
            finally:
                connection.close()
            if not error:
                return redirect(url_for("login", registered="1"))
    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        connection = get_connection()
        user = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            stored = user["password"]
            valid = False
            try:
                valid = check_password_hash(stored, password)
            except (ValueError, TypeError):
                valid = False
            # Migrate legacy demo accounts whose passwords were stored as plain text.
            if not valid and stored == password:
                valid = True
                connection.execute("UPDATE users SET password=? WHERE user_id=?", (generate_password_hash(password), user["user_id"]))
                connection.commit()
            if valid:
                session["user_id"] = user["user_id"]
                session["name"] = user["name"]
                connection.close()
                return redirect(url_for("search"))
        connection.close()
        error = "Email or password was not recognised. Check your details and try again."
    return render_template("login.html", error=error, registered=request.args.get("registered") == "1")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/search", methods=["GET", "POST"])
def search():
    if "user_id" not in session:
        return redirect(url_for("login"))
    destinations = all_destinations()
    origin_cities = [item for item in destinations if not _is_site_destination(item)]
    if request.method == "POST":
        destination = request.form.get("destination", "").strip() or "__recommend__"
        if destination != "__recommend__" and destination not in {item["name"] for item in destinations}:
            return render_template("search.html", name=session.get("name", "traveller"), destinations=destinations,
                                   origin_cities=origin_cities, today=date.today().isoformat(),
                                   default_travel_date=(date.today() + timedelta(days=2)).isoformat(),
                                   error="Choose a destination from the suggestions, or leave it blank for recommendations."), 400
        origin = request.form.get("origin", "Pune")
        interest = request.form.get("interest", "Any interest")
        try:
            budget = max(1000, min(2000000, int(request.form.get("budget", "15000"))))
            days = max(1, min(30, int(request.form.get("days", "3"))))
            travellers = max(1, min(20, int(request.form.get("travellers", "2"))))
            travel_date = date.fromisoformat(request.form.get("travel_date", "").strip())
            if travel_date < date.today():
                raise ValueError("Travel date cannot be in the past.")
        except ValueError:
            return render_template("search.html", name=session.get("name", "traveller"), destinations=destinations, origin_cities=origin_cities,
                                   today=date.today().isoformat(), default_travel_date=(date.today() + timedelta(days=2)).isoformat(),
                                   error="Enter valid budget, duration, travellers and a travel date that is today or later."), 400
        target = "recommendations" if destination == "__recommend__" else "results"
        params = dict(origin=origin, interest=interest, budget=budget, days=days, travellers=travellers, travel_date=travel_date.isoformat())
        if target == "results":
            params["destination"] = destination
        return redirect(url_for(target, **params))
    return render_template("search.html", name=session.get("name", "traveller"), destinations=destinations, origin_cities=origin_cities,
                           today=date.today().isoformat(), default_travel_date=(date.today() + timedelta(days=2)).isoformat())


@app.route("/recommendations")
def recommendations():
    try:
        budget = max(1000, min(2000000, int(request.args.get("budget", 15000))))
        days = max(1, min(30, int(request.args.get("days", 3))))
        travellers = max(1, min(20, int(request.args.get("travellers", 2))))
    except ValueError:
        return redirect(url_for("search"))
    interest = request.args.get("interest", "Any interest")
    origin = request.args.get("origin", "Pune")
    travel_date = request.args.get("travel_date", "")
    feedback_map = {}
    user_id = session.get("user_id")
    if user_id:
        connection = get_connection()
        if interest.casefold() in {"", "any", "any interest", "no preference"}:
            rows = connection.execute("""SELECT destination_name, SUM(signal) AS signal_sum, COUNT(*) AS count
                FROM recommendation_feedback WHERE user_id=? GROUP BY destination_name""", (user_id,)).fetchall()
        else:
            rows = connection.execute("""SELECT destination_name, SUM(signal) AS signal_sum, COUNT(*) AS count
                FROM recommendation_feedback WHERE user_id=? AND lower(coalesce(interest,''))=lower(?)
                GROUP BY destination_name""", (user_id, interest)).fetchall()
        connection.close()
        feedback_map = {row["destination_name"]: {"signal_sum": row["signal_sum"], "count": row["count"]} for row in rows}
    ranked = recommend_destinations(budget, days, travellers, interest, destination_map(), top_n=6,
                                    origin_name=origin, travel_date=travel_date, feedback=feedback_map)
    return render_template("recommendations.html", recommendations=ranked, budget=budget, days=days,
                           travellers=travellers, interest=interest, origin=origin, travel_date=travel_date,
                           feedback_saved=request.args.get("feedback") == "saved")


@app.route("/recommendation-feedback", methods=["POST"])
def recommendation_feedback():
    if "user_id" not in session:
        return redirect(url_for("login"))
    destination_name = request.form.get("destination_name", "").strip()
    try:
        signal = int(request.form.get("signal", "0"))
        budget = max(1000, min(2000000, int(request.form.get("budget", 15000))))
        days = max(1, min(30, int(request.form.get("days", 3))))
        travellers = max(1, min(20, int(request.form.get("travellers", 2))))
    except ValueError:
        return redirect(url_for("search"))
    valid_names = set(destination_map())
    if not destination_name or destination_name not in valid_names or signal not in (-1, 1):
        return redirect(url_for("search"))
    interest = request.form.get("interest", "Any interest")
    origin = request.form.get("origin", "Pune")
    travel_date = request.form.get("travel_date", "")
    connection = get_connection()
    connection.execute("""INSERT INTO recommendation_feedback
        (user_id, destination_name, signal, interest, travel_date) VALUES (?, ?, ?, ?, ?)""",
        (session["user_id"], destination_name, signal, interest, travel_date))
    connection.commit()
    connection.close()
    # The next page load reranks using this user's accumulated likes/dislikes.
    return redirect(url_for("recommendations", origin=origin, interest=interest, budget=budget, days=days,
                            travellers=travellers, travel_date=travel_date, feedback="saved"))


@app.route("/results")
def results():
    destination_name = request.args.get("destination", "Goa")
    destinations = destination_map()
    if destination_name not in destinations:
        return redirect(url_for("search"))
    destination = destinations[destination_name]
    interest = request.args.get("interest", "Any interest")
    travel_date = request.args.get("travel_date", "")
    origin_name = request.args.get("origin", "Pune")
    origin = destinations.get(origin_name, destinations.get("Pune"))
    try:
        budget = max(1000, min(2000000, int(request.args.get("budget", 15000))))
        days = max(1, min(30, int(request.args.get("days", destination.get("ideal_days") or 3))))
        travellers = max(1, min(20, int(request.args.get("travellers", 2))))
    except ValueError:
        return redirect(url_for("search"))

    connection = get_connection()
    all_places = [dict(row) for row in connection.execute("SELECT * FROM places WHERE location=? ORDER BY category, name", (destination_name,)).fetchall()]
    connection.close()
    if not all_places:
        # Keep the selected destination itself as a mappable place if custom DB rows are missing.
        all_places = [{"name": destination_name, "location": destination_name, "category": destination.get("category", "Travel"),
                       "description": destination.get("description", "Selected destination"),
                       "latitude": destination.get("latitude"), "longitude": destination.get("longitude")}]
    if interest not in ("Any interest", "Any", ""):
        if interest.casefold() == "forts":
            filtered = [place for place in all_places if "fort" in str(place["name"]).casefold() or str(place["category"]).casefold() == "forts"]
        else:
            filtered = [place for place in all_places if str(place["category"]).casefold() == interest.casefold()]
        places = filtered or all_places
    else:
        places = all_places

    map_places = [{key: place.get(key) for key in ("name", "category", "latitude", "longitude", "description")} for place in all_places]
    flight_query = quote_plus(f"Flights from {origin['name']} to {destination_name}")
    flight_search_url = f"https://www.google.com/travel/flights?q={flight_query}&curr=INR"
    exact_query = quote_plus(f"{destination_name}, {destination.get('location', '')}, India")
    maps_destination_url = f"https://www.google.com/maps/dir/?api=1&origin={quote_plus(origin['name'] + ', India')}&destination={exact_query}"
    hotel_maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus('hotels near ' + destination_name + ', ' + str(destination.get('location', 'India')))}"
    booking_url = f"https://www.booking.com/searchresults.html?ss={quote_plus(destination_name + ', ' + str(destination.get('location', 'India')))}"
    return render_template("results.html", destination=destination, destination_name=destination_name,
        destination_places=all_places, places=places, origin=origin, origin_name=origin["name"],
        interest=interest, budget=budget, days=days, travellers=travellers,
        map_places=map_places, travel_date=travel_date,
        flight_search_url=flight_search_url, maps_destination_url=maps_destination_url,
        hotel_maps_url=hotel_maps_url, booking_url=booking_url,
        train_search_url="https://www.irctc.co.in/nget/train-search")


@app.route("/itinerary")
def itinerary():
    destination = request.args.get("destination", "Goa")
    try:
        days = max(1, min(30, int(request.args.get("days", 3))))
    except ValueError:
        days = 3
    connection = get_connection()
    places = [dict(row) for row in connection.execute("SELECT * FROM places WHERE location=? ORDER BY name", (destination,)).fetchall()]
    connection.close()
    if not places:
        return redirect(url_for("search"))
    return render_template("itinerary.html", destination=destination, days=days, places=places,
                           budget=request.args.get("budget", "15000"), travellers=request.args.get("travellers", "2"),
                           interest=request.args.get("interest", "Any interest"), origin=request.args.get("origin", "Pune"),
        travel_date=request.args.get("travel_date", ""))


if __name__ == "__main__":
    create_database()
    try:
        from train_model import train
        model_path = BASE_DIR / "models" / "trip_recommender.json"
        # Retrain when the CSV has been updated since the model artifact was created.
        data_path = BASE_DIR / "data" / "recommendation_training.csv"
        if (not model_path.exists()) or (data_path.exists() and data_path.stat().st_mtime > model_path.stat().st_mtime):
            train()
    except Exception as exc:
        print(f"Recommendation model setup note: {exc}")
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print("\nTripGenie is starting.")
    print(f"Open on this computer: http://127.0.0.1:{port}")
    print("To use on a phone: connect to the same Wi-Fi, run 'ipconfig' on this PC, then open http://<PC-IPv4-address>:" + str(port))
    print("Do not type 0.0.0.0 into the browser; it is the server bind address.\n")
    app.run(host=host, port=port, debug=debug)
