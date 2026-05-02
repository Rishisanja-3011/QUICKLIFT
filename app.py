from flask import Flask, request, redirect, render_template, url_for, session, flash, g, jsonify, send_from_directory
from flask_mail import Mail, Message
import json
import math
import random
try:
    from authlib.integrations.flask_client import OAuth
except Exception:
    OAuth = None
import mysql.connector
import os
import requests
from datetime import datetime, date as dt_date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)

# ── Email config ──────────────────────────────────────────────
app.config['MAIL_SERVER']   = 'smtp.gmail.com'
app.config['MAIL_PORT']     = 587
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = 'sanjarishi99@gmail.com'
app.config['MAIL_PASSWORD'] = 'luufzfvkyplvevxo'
mail = Mail(app)
app.secret_key = "Patelbhai_here_3011"

# ── DB config ─────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "Patel_2101",
    "database": "quicklift"
}

ROUTE_SAMPLE_EVERY_KM = float(os.getenv("ROUTE_SAMPLE_EVERY_KM", "15"))
MAX_INTERMEDIATE_STOPS = int(os.getenv("MAX_INTERMEDIATE_STOPS", "8"))
GEOCODER_PROVIDER = os.getenv("GEOCODER_PROVIDER", "photon").lower()
ENABLE_NOMINATIM_FALLBACK = os.getenv("ENABLE_NOMINATIM_FALLBACK", "false").lower() == "true"
GEOCODER_TIMEOUT_SECONDS = int(os.getenv("GEOCODER_TIMEOUT_SECONDS", "4"))
GEOCODER_USER_AGENT = os.getenv("GEOCODER_USER_AGENT", "QuickLift/1.0 ride-stop-extractor")

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
        g.cursor = g.db.cursor(dictionary=True, buffered=True)
    return g.db, g.cursor

@app.teardown_appcontext
def close_db(exception=None):
    cursor = g.pop('cursor', None)
    db     = g.pop('db', None)
    if cursor: cursor.close()
    if db and db.is_connected(): db.close()

# ── Google OAuth ──────────────────────────────────────────────
oauth  = OAuth(app) if OAuth else None
google = oauth.register(
    name='google',
    client_id='853368867067-agsdp0bjm4c4q56j29pjrppqlh0fff63.apps.googleusercontent.com',
    client_secret='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',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
) if oauth else None

# ── File uploads ──────────────────────────────────────────────
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ── APScheduler ───────────────────────────────────────────────
scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def get_username():
    user_data = session.get('user')
    if not user_data: return None
    return user_data.get('username') if isinstance(user_data, dict) else user_data[1]

def get_road_distance(lat1, lon1, lat2, lon2):
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        response = requests.get(url, timeout=5).json()
        return round(response['routes'][0]['distance'] / 1000, 2)
    except Exception as e:
        print(f"Distance calculation error: {e}")
        return 0

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def add_column_if_missing(cursor, table_name, column_definition):
    try:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
    except mysql.connector.Error as err:
        if err.errno != 1060:
            raise

def ensure_multi_stop_schema():
    try:
        schema_db = mysql.connector.connect(**DB_CONFIG)
        schema_cursor = schema_db.cursor()
        schema_cursor.execute("""
            CREATE TABLE IF NOT EXISTS ride_stops (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ride_id INT NOT NULL,
                stop_name VARCHAR(255) NOT NULL,
                latitude DECIMAL(10,8),
                longitude DECIMAL(11,8),
                distance_from_start FLOAT NOT NULL DEFAULT 0,
                stop_order INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ride_order (ride_id, stop_order),
                INDEX idx_stop_name (stop_name),
                CONSTRAINT fk_ride_stops_ride
                    FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE
            )
        """)
        schema_cursor.execute("""
            CREATE TABLE IF NOT EXISTS geocode_cache (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cache_key VARCHAR(64) NOT NULL UNIQUE,
                latitude DECIMAL(10,8),
                longitude DECIMAL(11,8),
                place_name VARCHAR(255),
                provider VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        add_column_if_missing(schema_cursor, "rides", "route_geojson MEDIUMTEXT NULL")
        add_column_if_missing(schema_cursor, "rides", "duration_minutes INT NULL")
        add_column_if_missing(schema_cursor, "bookings", "pickup_stop_id INT NULL")
        add_column_if_missing(schema_cursor, "bookings", "drop_stop_id INT NULL")
        add_column_if_missing(schema_cursor, "bookings", "pickup_name VARCHAR(255) NULL")
        add_column_if_missing(schema_cursor, "bookings", "drop_name VARCHAR(255) NULL")
        add_column_if_missing(schema_cursor, "bookings", "segment_distance_km DECIMAL(10,2) NULL")
        add_column_if_missing(schema_cursor, "bookings", "booked_price DECIMAL(10,2) NULL")
        schema_db.commit()
        schema_cursor.close()
        schema_db.close()
    except Exception as e:
        print(f"Multi-stop schema check skipped: {e}")

def haversine_km(lat1, lon1, lat2, lon2):
    radius_km = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius_km * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def get_full_route(lat1, lon1, lat2, lon2):
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {
        "overview": "full",
        "geometries": "geojson"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        route = data["routes"][0]
        return {
            "distance_km": round(route.get("distance", 0) / 1000, 2),
            "duration_minutes": round(route.get("duration", 0) / 60),
            "geometry": route.get("geometry") or {"type": "LineString", "coordinates": []}
        }
    except Exception as e:
        print(f"Full route error: {e}")
        return None

def _route_coordinates(route_geometry):
    if isinstance(route_geometry, str):
        try:
            route_geometry = json.loads(route_geometry)
        except Exception:
            return []
    if not isinstance(route_geometry, dict):
        return []
    coordinates = route_geometry.get("coordinates") or []
    return [coord for coord in coordinates if isinstance(coord, (list, tuple)) and len(coord) >= 2]

def _geometry_distance_km(coordinates):
    total = 0.0
    for index in range(1, len(coordinates)):
        prev_lon, prev_lat = coordinates[index - 1][:2]
        lon, lat = coordinates[index][:2]
        total += haversine_km(safe_float(prev_lat), safe_float(prev_lon), safe_float(lat), safe_float(lon))
    return total

def _point_at_distance(coordinates, target_km):
    if not coordinates:
        return None
    if target_km <= 0:
        lon, lat = coordinates[0][:2]
        return safe_float(lat), safe_float(lon)
    travelled = 0.0
    for index in range(1, len(coordinates)):
        prev_lon, prev_lat = coordinates[index - 1][:2]
        lon, lat = coordinates[index][:2]
        prev_lat = safe_float(prev_lat)
        prev_lon = safe_float(prev_lon)
        lat = safe_float(lat)
        lon = safe_float(lon)
        segment_km = haversine_km(prev_lat, prev_lon, lat, lon)
        if segment_km <= 0:
            continue
        if travelled + segment_km >= target_km:
            ratio = (target_km - travelled) / segment_km
            return (
                prev_lat + ((lat - prev_lat) * ratio),
                prev_lon + ((lon - prev_lon) * ratio)
            )
        travelled += segment_km
    lon, lat = coordinates[-1][:2]
    return safe_float(lat), safe_float(lon)

def _clean_stop_name(name):
    if not name:
        return None
    cleaned = " ".join(str(name).strip().split())
    if not cleaned:
        return None
    lower = cleaned.lower()
    blocked = ("unnamed", "unknown", "national highway", "state highway", "expressway", "motorway")
    if any(item in lower for item in blocked):
        return None
    return cleaned[:255]

def _stop_key(name):
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())

def _pick_photon_place_name(properties):
    if not properties:
        return None
    priority_keys = ("city", "town", "village", "municipality", "locality", "district", "county", "name", "state")
    for key in priority_keys:
        candidate = _clean_stop_name(properties.get(key))
        if candidate:
            return candidate
    return None

def _reverse_geocode_photon(lat, lon):
    url = os.getenv("PHOTON_REVERSE_URL", "https://photon.komoot.io/reverse")
    params = {"lat": lat, "lon": lon, "limit": 3, "lang": "en"}
    response = requests.get(url, params=params, timeout=GEOCODER_TIMEOUT_SECONDS,
                            headers={"User-Agent": GEOCODER_USER_AGENT})
    response.raise_for_status()
    data = response.json()
    for feature in data.get("features", []):
        stop_name = _pick_photon_place_name(feature.get("properties", {}))
        if stop_name:
            return stop_name
    return None

def _reverse_geocode_nominatim(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "jsonv2",
        "lat": lat,
        "lon": lon,
        "zoom": 10,
        "addressdetails": 1
    }
    response = requests.get(url, params=params, timeout=GEOCODER_TIMEOUT_SECONDS,
                            headers={"User-Agent": GEOCODER_USER_AGENT})
    response.raise_for_status()
    data = response.json()
    address = data.get("address") or {}
    priority_keys = ("city", "town", "village", "municipality", "county", "state")
    for key in priority_keys:
        candidate = _clean_stop_name(address.get(key))
        if candidate:
            return candidate
    return _clean_stop_name(data.get("name") or data.get("display_name"))

def _geocode_cache_key(lat, lon):
    return f"{round(safe_float(lat), 4):.4f},{round(safe_float(lon), 4):.4f}"

def reverse_geocode(lat, lon):
    cache_key = _geocode_cache_key(lat, lon)
    db = cursor = None
    try:
        db, cursor = get_db()
        cursor.execute("SELECT place_name FROM geocode_cache WHERE cache_key = %s", (cache_key,))
        cached = cursor.fetchone()
        if cached and cached.get("place_name"):
            return cached["place_name"]
    except Exception as e:
        print(f"Geocode cache read skipped: {e}")

    providers = [GEOCODER_PROVIDER]
    if GEOCODER_PROVIDER != "photon":
        providers.append("photon")
    if ENABLE_NOMINATIM_FALLBACK and "nominatim" not in providers:
        providers.append("nominatim")

    provider_used = None
    stop_name = None
    for provider in providers:
        try:
            if provider == "photon":
                stop_name = _reverse_geocode_photon(lat, lon)
            elif provider == "nominatim":
                stop_name = _reverse_geocode_nominatim(lat, lon)
            if stop_name:
                provider_used = provider
                break
        except Exception as e:
            print(f"{provider} reverse geocode failed: {e}")

    if stop_name and cursor:
        try:
            cursor.execute("""
                INSERT INTO geocode_cache (cache_key, latitude, longitude, place_name, provider)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE place_name = VALUES(place_name), provider = VALUES(provider)
            """, (cache_key, lat, lon, stop_name, provider_used))
        except Exception as e:
            print(f"Geocode cache write skipped: {e}")
    return stop_name

def extract_stops(route_geometry):
    coordinates = _route_coordinates(route_geometry)
    if len(coordinates) < 2:
        return []

    geometry_km = _geometry_distance_km(coordinates)
    if geometry_km < ROUTE_SAMPLE_EVERY_KM:
        return []

    sample_count = min(MAX_INTERMEDIATE_STOPS, int(geometry_km // ROUTE_SAMPLE_EVERY_KM))
    if sample_count <= 0:
        return []

    spacing_km = geometry_km / (sample_count + 1)
    stops = []
    seen_names = set()
    consecutive_geocode_misses = 0
    for index in range(1, sample_count + 1):
        distance_from_start = round(spacing_km * index, 2)
        point = _point_at_distance(coordinates, distance_from_start)
        if not point:
            continue
        lat, lon = point
        stop_name = reverse_geocode(lat, lon)
        stop_key = _stop_key(stop_name)
        if not stop_name or stop_key in seen_names:
            consecutive_geocode_misses += 1
            if consecutive_geocode_misses >= 3:
                break
            continue
        consecutive_geocode_misses = 0
        seen_names.add(stop_key)
        stops.append({
            "stop_name": stop_name,
            "latitude": round(lat, 8),
            "longitude": round(lon, 8),
            "distance_from_start": distance_from_start
        })
    return stops

def _build_ride_stops(leaving_from, going_to, start_lat, start_lon, dest_lat, dest_lon, distance_km, route_geometry):
    total_distance = max(safe_float(distance_km), 0.0)
    start_stop = {
        "stop_name": _clean_stop_name(leaving_from) or "Start",
        "latitude": round(safe_float(start_lat), 8),
        "longitude": round(safe_float(start_lon), 8),
        "distance_from_start": 0.0
    }
    end_stop = {
        "stop_name": _clean_stop_name(going_to) or "Destination",
        "latitude": round(safe_float(dest_lat), 8),
        "longitude": round(safe_float(dest_lon), 8),
        "distance_from_start": round(total_distance, 2)
    }
    raw_stops = [start_stop] + extract_stops(route_geometry) + [end_stop]
    cleaned = []
    seen = set()
    for index, stop in enumerate(raw_stops):
        is_endpoint = index == 0 or index == len(raw_stops) - 1
        stop_name = _clean_stop_name(stop.get("stop_name"))
        if not stop_name:
            continue
        distance = safe_float(stop.get("distance_from_start"))
        if not is_endpoint:
            if distance < 3 or (total_distance and distance > total_distance - 3):
                continue
            if cleaned and abs(distance - safe_float(cleaned[-1].get("distance_from_start"))) < 5:
                continue
        key = _stop_key(stop_name)
        if key in seen and not is_endpoint:
            continue
        seen.add(key)
        stop["stop_name"] = stop_name
        stop["distance_from_start"] = round(distance, 2)
        cleaned.append(stop)

    if len(cleaned) < 2:
        cleaned = [start_stop, end_stop]
    for order, stop in enumerate(cleaned):
        stop["stop_order"] = order
    return cleaned

def save_stops_to_db(ride_id, stops):
    db, cursor = get_db()
    cursor.execute("DELETE FROM ride_stops WHERE ride_id = %s", (ride_id,))
    for order, stop in enumerate(stops):
        cursor.execute("""
            INSERT INTO ride_stops
                (ride_id, stop_name, latitude, longitude, distance_from_start, stop_order)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            ride_id,
            stop.get("stop_name"),
            stop.get("latitude"),
            stop.get("longitude"),
            stop.get("distance_from_start", 0),
            stop.get("stop_order", order)
        ))

def get_ride_stops(cursor, ride_id):
    try:
        cursor.execute("""
            SELECT id, ride_id, stop_name, latitude, longitude, distance_from_start, stop_order
            FROM ride_stops
            WHERE ride_id = %s
            ORDER BY stop_order ASC
        """, (ride_id,))
        return cursor.fetchall()
    except Exception as e:
        print(f"Ride stops fetch skipped: {e}")
        return []

def attach_stops_to_rides(cursor, rides):
    if not rides:
        return rides
    ride_ids = [ride["id"] for ride in rides if ride.get("id")]
    if not ride_ids:
        return rides
    try:
        placeholders = ",".join(["%s"] * len(ride_ids))
        cursor.execute(f"""
            SELECT ride_id, stop_name, stop_order
            FROM ride_stops
            WHERE ride_id IN ({placeholders})
            ORDER BY ride_id, stop_order
        """, tuple(ride_ids))
        stops_by_ride = {}
        for stop in cursor.fetchall():
            stops_by_ride.setdefault(stop["ride_id"], []).append(stop["stop_name"])
        for ride in rides:
            ride["stops"] = stops_by_ride.get(ride.get("id"), [])
    except Exception as e:
        print(f"Ride stop summary skipped: {e}")
    return rides

def calculate_segment_price(ride, segment_distance_km):
    total_distance = safe_float(ride.get("distance_km"))
    full_seat_price = safe_float(ride.get("price_per_seat") or ride.get("total_price"))
    segment_distance = safe_float(segment_distance_km)
    if total_distance <= 0 or segment_distance <= 0:
        return round(full_seat_price, 2)
    return round(max(0, (segment_distance / total_distance) * full_seat_price), 2)

def find_rides_by_stops(start, end, ride_date=None):
    db, cursor = get_db()
    start = (start or "").strip()
    end = (end or "").strip()

    if not start or not end:
        query = "SELECT * FROM rides WHERE seats > 0"
        params = []
        if ride_date:
            query += " AND date = %s"
            params.append(ride_date)
        query += " ORDER BY date ASC, time ASC"
        cursor.execute(query, tuple(params))
        rides = cursor.fetchall()
        return attach_stops_to_rides(cursor, rides)

    try:
        params = [f"%{start}%", f"%{end}%"]
        date_filter = ""
        if ride_date:
            date_filter = " AND r.date = %s"
            params.append(ride_date)
        cursor.execute(f"""
            SELECT DISTINCT r.*,
                   pickup.id AS matched_pickup_stop_id,
                   dropoff.id AS matched_drop_stop_id,
                   pickup.stop_name AS matched_pickup_name,
                   dropoff.stop_name AS matched_drop_name,
                   ROUND(dropoff.distance_from_start - pickup.distance_from_start, 2) AS segment_distance_km
            FROM rides r
            JOIN ride_stops pickup ON pickup.ride_id = r.id
            JOIN ride_stops dropoff ON dropoff.ride_id = r.id
                 AND pickup.stop_order < dropoff.stop_order
            WHERE pickup.stop_name LIKE %s
              AND dropoff.stop_name LIKE %s
              AND r.seats > 0
              {date_filter}
            ORDER BY r.date ASC, r.time ASC
        """, tuple(params))
        rides = cursor.fetchall()
        for ride in rides:
            ride["segment_price"] = calculate_segment_price(ride, ride.get("segment_distance_km"))
        if rides:
            return attach_stops_to_rides(cursor, rides)
    except Exception as e:
        print(f"Stop search skipped: {e}")

    params = [f"%{start}%", f"%{end}%"]
    date_filter = ""
    if ride_date:
        date_filter = " AND date = %s"
        params.append(ride_date)
    cursor.execute(f"""
        SELECT * FROM rides
        WHERE leaving_from LIKE %s
          AND going_to LIKE %s
          AND seats > 0
          {date_filter}
        ORDER BY date ASC, time ASC
    """, tuple(params))
    rides = cursor.fetchall()
    return attach_stops_to_rides(cursor, rides)

def get_segment_from_stops(cursor, ride_id, pickup_stop_id, drop_stop_id):
    if not pickup_stop_id or not drop_stop_id:
        return None
    cursor.execute("""
        SELECT pickup.id AS pickup_stop_id,
               dropoff.id AS drop_stop_id,
               pickup.stop_name AS pickup_name,
               dropoff.stop_name AS drop_name,
               pickup.stop_order AS pickup_order,
               dropoff.stop_order AS drop_order,
               ROUND(dropoff.distance_from_start - pickup.distance_from_start, 2) AS segment_distance_km
        FROM ride_stops pickup
        JOIN ride_stops dropoff ON dropoff.ride_id = pickup.ride_id
        WHERE pickup.ride_id = %s
          AND pickup.id = %s
          AND dropoff.id = %s
          AND pickup.stop_order < dropoff.stop_order
    """, (ride_id, pickup_stop_id, drop_stop_id))
    return cursor.fetchone()

ensure_multi_stop_schema()

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
    msg = Message("QuickLift OTP Verification",
                  sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f"<-----------QuickLift---------->\n Your OTP for QuickLift verification is: {otp}"
    mail.send(msg)

# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user' in session: return redirect('/dashboard')
    return redirect('/register')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ── Google OAuth ──────────────────────────────────────────────
@app.route('/login/google')
def google_login():
    if not google: return redirect('/login')
    return google.authorize_redirect(url_for('google_callback', _external=True))

@app.route('/auth/google/callback')
def google_callback():
    if not google: return redirect('/login')
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    if user_info:
        db, cursor = get_db()
        cursor.execute("SELECT * FROM userdata WHERE email=%s", (user_info['email'],))
        db_user = cursor.fetchone()
        session['user'] = db_user if db_user else {
            'username': user_info.get('email').split('@')[0],
            'fullname': user_info.get('name'),
            'email':    user_info.get('email'),
            'is_google': True
        }
        return redirect('/dashboard')
    return redirect('/login')

# ── Login ─────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('login.html', error="All fields required")
        try:
            db, cursor = get_db()
            cursor.execute("SELECT * FROM userdata WHERE username=%s AND passwords=%s", (username, password))
            result = cursor.fetchone()
            if result:
                session['user'] = result
                return redirect('/dashboard')
            return render_template('login.html', error="Invalid username or password")
        except Exception as e:
            print(f"Login Error: {e}")
            return render_template('login.html', error="Database error. Please try again.")
    return render_template('login.html')

# ── Register ──────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname         = request.form.get('fullname')
        username         = request.form.get('username')
        email            = request.form.get('email')
        contact          = request.form.get('contact')
        city             = request.form.get('city')
        password         = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        gender           = request.form.get('gender')
        file             = request.files.get('file')        # profile photo
        id_file_obj      = request.files.get('id_file')     # ID proof

        if not all([fullname, username, email, contact, city,
                    password, confirm_password, gender, file, id_file_obj]):
            return render_template('register.html', error="Please fill in all fields including photo and ID proof")
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")

        # Save profile photo
        file_path = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_path))

        # Save ID proof
        id_file_path = id_file_obj.filename
        id_file_obj.save(os.path.join(app.config['UPLOAD_FOLDER'], id_file_path))

        db, cursor = get_db()
        cursor.execute("SELECT * FROM userdata WHERE username=%s OR email=%s", (username, email))
        if cursor.fetchone():
            return render_template("register.html", error="Username or email already exists")

        session['register_data'] = {
            "fullname":     fullname,
            "username":     username,
            "email":        email,
            "contact":      contact,
            "city":         city,
            "gender":       gender,
            "file_path":    file_path,
            "id_file_path": id_file_path,
            "password":     password
        }
        otp = generate_otp()
        session['otp']      = otp
        session['otp_type'] = "register"
        send_otp_email(email, otp)
        return render_template("otp.html")
    return render_template('register.html')

# ── Verify OTP ────────────────────────────────────────────────
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    user_otp = request.form.get('otp')
    if user_otp == session.get('otp'):
        if session.get('otp_type') == "register":
            data = session.get('register_data')
            db, cursor = get_db()
            cursor.execute(
                """INSERT INTO userdata
                   (fullname, username, email, phnumber, city, gender, files, id_file, passwords)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (data['fullname'], data['username'], data['email'], data['contact'],
                 data['city'], data['gender'], data['file_path'],
                 data['id_file_path'], data['password'])
            )
            db.commit()
            session.pop('otp', None)
            session.pop('otp_type', None)
            session.pop('register_data', None)
            flash("Registration successful. Please login.")
            return redirect('/login')
        elif session.get('otp_type') == "reset":
            return redirect('/reset-password')
    else:
        return render_template("otp.html", error="Invalid OTP")

# ── Forgot / Reset Password ───────────────────────────────────
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        db, cursor = get_db()
        cursor.execute("SELECT * FROM userdata WHERE email=%s", (email,))
        if not cursor.fetchone():
            return render_template("forgot-password.html", error="Email not found")
        otp = generate_otp()
        session['otp'] = otp; session['otp_type'] = "reset"; session['reset_email'] = email
        send_otp_email(email, otp)
        return render_template("otp.html")
    return render_template("forgot-password.html")

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form.get('password')
        email = session.get('reset_email')
        db, cursor = get_db()
        cursor.execute("UPDATE userdata SET passwords=%s WHERE email=%s", (new_password, email))
        db.commit()
        flash("Password updated successfully")
        return redirect('/login')
    return render_template("reset-password.html")

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# ── Dashboard ─────────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    user_name  = get_username()
    db, cursor = get_db()
    try:
        cursor.execute("DELETE FROM rides WHERE date < CURDATE() OR (date = CURDATE() AND time < CURTIME())")
        db.commit()
    except Exception as e:
        print("Cleanup error:", e); db.rollback()

    cursor.execute("SELECT * FROM rides WHERE username != %s AND seats > 0 ORDER BY date ASC LIMIT 3", (user_name,))
    recent_rides = cursor.fetchall()
    recent_rides = attach_stops_to_rides(cursor, recent_rides)
    cursor.execute("SELECT COUNT(*) as total FROM bookings WHERE passenger_username = %s", (user_name,))
    booking_count = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM rides WHERE username = %s", (user_name,))
    published_count = cursor.fetchone()['total']
    stats = {
        'co2_saved':      round((booking_count + published_count) * 2.15, 1),
        'network_status': "Active" if recent_rides else "Searching",
        'total_rides':    booking_count + published_count
    }
    return render_template('dashboard.html', user=session['user'], recent_rides=recent_rides, stats=stats)

# ── Publish Ride ──────────────────────────────────────────────
@app.route('/publish', methods=['GET', 'POST'])
def publish():
    if 'user' not in session: return redirect('/login')
    if request.method == 'POST':
        try:
            start_lat = float(request.form.get('start_lat'))
            start_lon = float(request.form.get('start_lon'))
            dest_lat  = float(request.form.get('dest_lat'))
            dest_lon  = float(request.form.get('dest_lon'))
        except (TypeError, ValueError):
            flash("City lookup failed. Please select valid start and destination cities.", "error")
            return redirect('/publish')
        leaving_from = request.form.get('leaving_from')
        going_to     = request.form.get('going_to')
        date         = request.form.get('date')
        time         = request.form.get('time')
        seats        = int(request.form.get('seats', '1'))
        vehicle      = request.form.get('vehicle')
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d').date()
            today = dt_date.today()
            if parsed_date < today:
                flash("Cannot publish rides in the past.", "error"); return redirect('/publish')
            if parsed_date > today + timedelta(days=15):
                flash("Cannot publish rides more than 15 days in advance.", "error"); return redirect('/publish')
        except Exception: pass
        route_data = get_full_route(start_lat, start_lon, dest_lat, dest_lon)
        if route_data:
            km = route_data["distance_km"]
            route_geometry = route_data["geometry"]
            route_geojson = json.dumps(route_geometry)
            duration_minutes = route_data["duration_minutes"]
        else:
            km = get_road_distance(start_lat, start_lon, dest_lat, dest_lon)
            route_geometry = {"type": "LineString", "coordinates": [[start_lon, start_lat], [dest_lon, dest_lat]]}
            route_geojson = json.dumps(route_geometry)
            duration_minutes = None
        total_price    = 40 + (km * 12)
        price_per_seat = round(total_price / max(seats, 1), 2)
        user_name  = get_username()
        db, cursor = get_db()
        try:
            cursor.execute(
                """INSERT INTO rides (username, leaving_from, going_to, date, time, seats,
                   vehicle, distance_km, price_per_seat, total_price, route_geojson, duration_minutes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (user_name, leaving_from, going_to, date, time, seats, vehicle, km,
                 price_per_seat, round(total_price, 2), route_geojson, duration_minutes)
            )
            ride_id = cursor.lastrowid
            stops = []
            try:
                stops = _build_ride_stops(leaving_from, going_to, start_lat, start_lon,
                                          dest_lat, dest_lon, km, route_geometry)
                save_stops_to_db(ride_id, stops)
            except Exception as stop_error:
                print(f"Stop extraction skipped for ride {ride_id}: {stop_error}")
            db.commit()
            if stops:
                flash(f"Ride published successfully with {len(stops)} route stops!", "success")
            else:
                flash("Ride published successfully. Route stops will be available after the schema/geocoder is ready.", "success")
        except Exception as e:
            db.rollback()
            print("INSERT FAILED:", e)
            flash("Ride could not be published. Please try again.", "error")
        return render_template('publish.html', user=session['user'],
                               calculated_km=km, total_price=round(total_price, 2), price_per_seat=price_per_seat)
    return render_template('publish.html', user=session['user'])

# ── Find Ride ─────────────────────────────────────────────────
@app.route('/find-ride', methods=['GET', 'POST'])
def find_ride():
    if 'user' not in session: return redirect('/login')
    db, cursor = get_db()
    try:
        cursor.execute("DELETE FROM rides WHERE date < CURDATE() OR (date = CURDATE() AND time < CURTIME())")
        db.commit()
    except Exception as e:
        print("Cleanup error:", e); db.rollback()
    if request.method == 'POST':
        leaving_from = request.form.get('from')
        going_to     = request.form.get('to')
        ride_date    = request.form.get('date')
        rides = find_rides_by_stops(leaving_from, going_to, ride_date)
    else:
        cursor.execute("SELECT * FROM rides WHERE seats > 0 ORDER BY date ASC")
        rides = attach_stops_to_rides(cursor, cursor.fetchall())
    return render_template('findride.html', user=session['user'], rides=rides)

# ── Reserve & Book ────────────────────────────────────────────
@app.route('/reserve/<int:ride_id>')
def reserve_page(ride_id):
    if 'user' not in session: return redirect('/login')
    db, cursor = get_db()
    cursor.execute("SELECT * FROM rides WHERE id = %s", (ride_id,))
    ride = cursor.fetchone()
    if not ride:
        flash("Ride not found!"); return redirect('/find-ride')
    stops = get_ride_stops(cursor, ride_id)
    selected_pickup_id = request.args.get('pickup_stop_id', type=int)
    selected_drop_id = request.args.get('drop_stop_id', type=int)
    if stops and (not selected_pickup_id or not selected_drop_id):
        selected_pickup_id = stops[0]["id"]
        selected_drop_id = stops[-1]["id"]
    selected_segment = get_segment_from_stops(cursor, ride_id, selected_pickup_id, selected_drop_id) if stops else None
    segment_price = calculate_segment_price(ride, selected_segment["segment_distance_km"]) if selected_segment else ride.get("price_per_seat")
    return render_template('reserve.html', user=session['user'], ride=ride, stops=stops,
                           selected_pickup_id=selected_pickup_id,
                           selected_drop_id=selected_drop_id,
                           selected_segment=selected_segment,
                           segment_price=segment_price)

@app.route('/book-ride/<int:ride_id>', methods=['GET', 'POST'])
def book_ride(ride_id):
    if 'user' not in session: return redirect('/login')
    user_name  = get_username()
    db, cursor = get_db()
    if request.method == 'GET':
        return redirect(url_for('reserve_page', ride_id=ride_id))

    cursor.execute("SELECT * FROM rides WHERE id = %s FOR UPDATE", (ride_id,))
    ride = cursor.fetchone()
    if not ride or ride['seats'] <= 0:
        db.rollback()
        flash("Sorry, no seats left for this ride."); return redirect('/find-ride')
    if ride['username'] == user_name:
        db.rollback()
        flash("You cannot book your own ride."); return redirect('/find-ride')

    pickup_stop_id = request.form.get('pickup_stop_id', type=int)
    drop_stop_id = request.form.get('drop_stop_id', type=int)
    ride_stops = get_ride_stops(cursor, ride_id)
    segment = get_segment_from_stops(cursor, ride_id, pickup_stop_id, drop_stop_id)

    if ride_stops and len(ride_stops) > 1 and (not pickup_stop_id or not drop_stop_id):
        db.rollback()
        flash("Please choose a pickup and drop point.", "error")
        return redirect(url_for('reserve_page', ride_id=ride_id))

    if pickup_stop_id or drop_stop_id:
        if not segment:
            db.rollback()
            flash("Please choose a valid pickup and drop point.", "error")
            return redirect(url_for('reserve_page', ride_id=ride_id))
        pickup_name = segment["pickup_name"]
        drop_name = segment["drop_name"]
        segment_distance_km = segment["segment_distance_km"]
        booked_price = calculate_segment_price(ride, segment_distance_km)
    else:
        pickup_name = ride["leaving_from"]
        drop_name = ride["going_to"]
        segment_distance_km = ride.get("distance_km")
        booked_price = ride.get("price_per_seat")

    try:
        cursor.execute("UPDATE rides SET seats = seats - 1 WHERE id = %s", (ride_id,))
        cursor.execute("""
            INSERT INTO bookings
                (ride_id, passenger_username, pickup_stop_id, drop_stop_id,
                 pickup_name, drop_name, segment_distance_km, booked_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            ride_id, user_name,
            segment["pickup_stop_id"] if segment else None,
            segment["drop_stop_id"] if segment else None,
            pickup_name, drop_name, segment_distance_km, booked_price
        ))
        db.commit()
        flash("Booking Successful! Track your driver below.", "success")
        return redirect(f'/track/{ride_id}')
    except Exception as e:
        db.rollback(); print(f"Sync Error: {e}"); return "Database Sync Error", 500

# ── Live Location ─────────────────────────────────────────────
@app.route('/update-location', methods=['POST'])
def update_location():
    if 'user' not in session: return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    lat = data.get('lat'); lon = data.get('lon')
    username = get_username()
    db, cursor = get_db()
    try:
        cursor.execute(
            """INSERT INTO user_locations (username, latitude, longitude) VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE latitude=%s, longitude=%s, updated_at=NOW()""",
            (username, lat, lon, lat, lon))
        db.commit()
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Location update error: {e}"); return jsonify({'error': str(e)}), 500

@app.route('/get-location/<int:ride_id>')
def get_location(ride_id):
    if 'user' not in session: return jsonify({'error': 'unauthorized'}), 401
    db, cursor = get_db()
    cursor.execute("SELECT username FROM rides WHERE id = %s", (ride_id,))
    ride = cursor.fetchone()
    if not ride: return jsonify({'error': 'ride not found'}), 404
    cursor.execute("SELECT latitude, longitude, updated_at FROM user_locations WHERE username = %s", (ride['username'],))
    loc = cursor.fetchone()
    if loc and loc['latitude']:
        return jsonify({'lat': loc['latitude'], 'lon': loc['longitude'], 'updated_at': str(loc['updated_at'])})
    return jsonify({'error': 'location not available yet'})

@app.route('/track/<int:ride_id>')
def track_ride(ride_id):
    if 'user' not in session: return redirect('/login')
    db, cursor = get_db()
    cursor.execute("SELECT * FROM rides WHERE id = %s", (ride_id,))
    ride = cursor.fetchone()
    if not ride:
        flash("Ride not found."); return redirect('/insights')
    cursor.execute("SELECT phnumber, fullname FROM userdata WHERE username = %s", (ride['username'],))
    driver = cursor.fetchone()
    cursor.execute("""
        SELECT pickup_name, drop_name, segment_distance_km, booked_price
        FROM bookings
        WHERE ride_id = %s AND passenger_username = %s
        ORDER BY booking_date DESC LIMIT 1
    """, (ride_id, get_username()))
    booking = cursor.fetchone()
    stops = get_ride_stops(cursor, ride_id)
    return render_template('tracking.html', user=session['user'], ride=ride, driver=driver,
                           ride_id=ride_id, booking=booking, stops=stops)

@app.route('/check-ride/<int:ride_id>')
def check_ride(ride_id):
    if 'user' not in session: return jsonify({'error': 'unauthorized'}), 401
    db, cursor = get_db()
    cursor.execute("SELECT id FROM rides WHERE id = %s", (ride_id,))
    return jsonify({'exists': cursor.fetchone() is not None})

# ── Insights ──────────────────────────────────────────────────
@app.route('/insights')
def insights():
    if 'user' not in session: return redirect('/login')
    user_name  = get_username()
    db, cursor = get_db()
    cursor.execute("""
        SELECT r.id as ride_id, r.leaving_from, r.going_to, r.date, r.time,
               r.price_per_seat, r.vehicle, r.username as driver_username,
               b.id as booking_id, b.status, b.booking_date,
               COALESCE(b.pickup_name, r.leaving_from) AS booking_from,
               COALESCE(b.drop_name, r.going_to) AS booking_to,
               COALESCE(b.segment_distance_km, r.distance_km) AS booked_distance_km,
               COALESCE(b.booked_price, r.price_per_seat) AS booked_price
        FROM bookings b JOIN rides r ON b.ride_id = r.id
        WHERE b.passenger_username = %s ORDER BY b.booking_date DESC
    """, (user_name,))
    bookings = cursor.fetchall()
    cursor.execute("""
        SELECT r.*, COUNT(b.id) as passenger_count
        FROM rides r LEFT JOIN bookings b ON b.ride_id = r.id
        WHERE r.username = %s GROUP BY r.id ORDER BY r.date ASC
    """, (user_name,))
    published = cursor.fetchall()
    stats = {
        'carbon_saved': round(len(bookings) * 2.15, 2),
        'total_rides':  len(bookings) + len(published)
    }
    return render_template('insights.html', user=session['user'],
                           bookings=bookings, published=published, stats=stats)

# ── Unbook ────────────────────────────────────────────────────
@app.route('/unbook/<int:booking_id>', methods=['POST'])
def unbook_ride(booking_id):
    if 'user' not in session: return redirect('/login')
    user_name  = get_username()
    db, cursor = get_db()
    cursor.execute("SELECT b.id, b.ride_id FROM bookings b WHERE b.id = %s AND b.passenger_username = %s",
                   (booking_id, user_name))
    booking = cursor.fetchone()
    if not booking:
        flash("Booking not found or unauthorized.", "error"); return redirect('/insights')
    try:
        cursor.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
        cursor.execute("UPDATE rides SET seats = seats + 1 WHERE id = %s", (booking['ride_id'],))
        db.commit()
        flash("Booking cancelled. Seat has been released.", "success")
    except Exception as e:
        db.rollback(); print(f"Unbook error: {e}"); flash("Something went wrong.", "error")
    return redirect('/insights')

# ── Cancel Ride ───────────────────────────────────────────────
@app.route('/cancel-ride/<int:ride_id>', methods=['POST'])
def cancel_ride(ride_id):
    if 'user' not in session: return redirect('/login')
    user_name  = get_username()
    db, cursor = get_db()
    cursor.execute("SELECT * FROM rides WHERE id = %s AND username = %s", (ride_id, user_name))
    ride = cursor.fetchone()
    if not ride:
        flash("Ride not found or unauthorized.", "error"); return redirect('/insights')
    cursor.execute("""
        SELECT u.email, u.fullname FROM bookings b
        JOIN userdata u ON b.passenger_username = u.username WHERE b.ride_id = %s
    """, (ride_id,))
    passengers = cursor.fetchall()
    try:
        cursor.execute("DELETE FROM bookings WHERE ride_id = %s", (ride_id,))
        cursor.execute("DELETE FROM rides WHERE id = %s", (ride_id,))
        db.commit()
        for passenger in passengers:
            try:
                msg = Message(subject="⚠️ QuickLift — Your ride has been cancelled",
                              sender=app.config['MAIL_USERNAME'], recipients=[passenger['email']])
                msg.body = f"<----------- QuickLift ----------->\n\nHi {passenger['fullname']},\n\nYour upcoming ride has been cancelled by the driver.\n\nCANCELLED RIDE:\n  From  : {ride['leaving_from']}\n  To    : {ride['going_to']}\n  Date  : {ride['date']} at {ride['time']}\n  Driver: @{ride['username']}\n\nPlease find another ride:\n  http://127.0.0.1:5000/find-ride\n\n— QuickLift Team"
                mail.send(msg)
            except Exception as e:
                print(f"Email error for {passenger['email']}: {e}")
        flash(f"Ride cancelled. {len(passengers)} passenger(s) notified by email.", "success")
    except Exception as e:
        db.rollback(); print(f"Cancel ride error: {e}"); flash("Something went wrong.", "error")
    return redirect('/insights')

# ── Ride Passengers ───────────────────────────────────────────
@app.route('/ride-passengers/<int:ride_id>')
def ride_passengers(ride_id):
    if 'user' not in session: return redirect('/login')
    user_name  = get_username()
    db, cursor = get_db()
    cursor.execute("SELECT * FROM rides WHERE id = %s AND username = %s", (ride_id, user_name))
    ride = cursor.fetchone()
    if not ride:
        flash("Ride not found or unauthorized."); return redirect('/insights')
    cursor.execute("""
        SELECT u.fullname, u.username, u.phnumber, u.city, u.gender, u.files,
               b.id as booking_id, b.booking_date,
               COALESCE(b.pickup_name, %s) AS pickup_name,
               COALESCE(b.drop_name, %s) AS drop_name,
               b.segment_distance_km,
               COALESCE(b.booked_price, %s) AS booked_price
        FROM bookings b JOIN userdata u ON b.passenger_username = u.username
        WHERE b.ride_id = %s ORDER BY b.booking_date ASC
    """, (ride['leaving_from'], ride['going_to'], ride['price_per_seat'], ride_id))
    passengers = cursor.fetchall()
    return render_template('ride_passengers.html', user=session['user'], ride=ride, passengers=passengers)

# ── Profile — view ────────────────────────────────────────────
@app.route('/profile/<username>')
def profile(username):
    if 'user' not in session: return redirect('/login')
    db, cursor = get_db()
    cursor.execute("SELECT * FROM userdata WHERE username = %s", (username,))
    profile_user = cursor.fetchone()
    if not profile_user:
        flash("User not found."); return redirect('/dashboard')
    cursor.execute("SELECT COUNT(*) as total FROM rides WHERE username = %s", (username,))
    rides_published = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM bookings WHERE passenger_username = %s", (username,))
    rides_taken = cursor.fetchone()['total']
    stats = {
        'rides_published': rides_published,
        'rides_taken':     rides_taken,
        'co2_saved':       round((rides_published + rides_taken) * 2.15, 1)
    }
    return render_template('profile.html', user=session['user'], profile=profile_user,
                           stats=stats, current_user=get_username())

# ── Profile — edit ────────────────────────────────────────────
@app.route('/edit-profile', methods=['POST'])
def edit_profile():
    if 'user' not in session: return redirect('/login')
    user_name    = get_username()
    db, cursor   = get_db()
    fullname     = request.form.get('fullname')
    new_username = request.form.get('username')
    city         = request.form.get('city')
    phnumber     = request.form.get('phnumber')
    photo        = request.files.get('photo')

    # Check new username not taken by someone else
    if new_username != user_name:
        cursor.execute("SELECT id FROM userdata WHERE username = %s", (new_username,))
        if cursor.fetchone():
            flash("Username already taken.", "error")
            return redirect(f'/profile/{user_name}')
    try:
        if photo and photo.filename:
            file_path = photo.filename
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], file_path))
            cursor.execute(
                "UPDATE userdata SET fullname=%s, username=%s, city=%s, phnumber=%s, files=%s WHERE username=%s",
                (fullname, new_username, city, phnumber, file_path, user_name)
            )
        else:
            cursor.execute(
                "UPDATE userdata SET fullname=%s, username=%s, city=%s, phnumber=%s WHERE username=%s",
                (fullname, new_username, city, phnumber, user_name)
            )
        db.commit()
        # Refresh session
        cursor.execute("SELECT * FROM userdata WHERE username = %s", (new_username,))
        session['user'] = cursor.fetchone()
        flash("Profile updated successfully!", "success")
        return redirect(f'/profile/{new_username}')
    except Exception as e:
        db.rollback(); print(f"Edit profile error: {e}")
        flash("Something went wrong. Please try again.", "error")
        return redirect(f'/profile/{user_name}')

# ── Scheduler ─────────────────────────────────────────────────
def send_ride_notifications():
    try:
        notif_db     = mysql.connector.connect(**DB_CONFIG)
        notif_cursor = notif_db.cursor(dictionary=True)
        notif_cursor.execute("""
            SELECT r.id, r.username, r.leaving_from, r.going_to, r.date, r.time,
                   u.phnumber, u.fullname, ul.latitude, ul.longitude
            FROM rides r JOIN userdata u ON r.username = u.username
            LEFT JOIN user_locations ul ON r.username = ul.username
            WHERE TIMESTAMP(r.date, r.time) > NOW()
              AND TIMESTAMP(r.date, r.time) <= DATE_ADD(NOW(), INTERVAL 5 MINUTE)
              AND r.reminder_sent = 0
        """)
        upcoming_rides = notif_cursor.fetchall()
        for ride in upcoming_rides:
            notif_cursor.execute("""
                SELECT b.passenger_username, u.email, u.fullname,
                       COALESCE(b.pickup_name, %s) AS pickup_name,
                       COALESCE(b.drop_name, %s) AS drop_name
                FROM bookings b
                JOIN userdata u ON b.passenger_username = u.username
                WHERE b.ride_id = %s AND b.status = 'Booked'
            """, (ride['leaving_from'], ride['going_to'], ride['id']))
            passengers = notif_cursor.fetchall()
            location_text = (
                f"Driver's current location: https://www.google.com/maps?q={ride['latitude']},{ride['longitude']}"
                if ride['latitude'] and ride['longitude']
                else "Driver location not available yet. Please contact them directly."
            )
            for passenger in passengers:
                try:
                    msg = Message(subject="🚗 QuickLift — Your ride departs in 5 minutes!",
                                  sender=app.config['MAIL_USERNAME'], recipients=[passenger['email']])
                    msg.body = f"<----------- QuickLift ----------->\n\nHi {passenger['fullname']},\n\nYour ride departs in ~5 minutes!\n\nFrom: {passenger['pickup_name']}\nTo  : {passenger['drop_name']}\nDriver: {ride['fullname']} (@{ride['username']})\nPhone : {ride['phnumber']}\n\n{location_text}\n\nTrack live: http://127.0.0.1:5000/track/{ride['id']}\n\nSafe travels!\n— QuickLift Team"
                    with app.app_context(): mail.send(msg)
                except Exception as e:
                    print(f"Email error for {passenger['email']}: {e}")
            notif_cursor.execute("UPDATE rides SET reminder_sent = 1 WHERE id = %s", (ride['id'],))
            notif_db.commit()
        notif_cursor.close(); notif_db.close()
    except Exception as e:
        print(f"Scheduler error: {e}")

def cleanup_expired_rides():
    try:
        cleanup_db = mysql.connector.connect(**DB_CONFIG)
        cleanup_cursor = cleanup_db.cursor()
        cleanup_cursor.execute("DELETE FROM rides WHERE TIMESTAMP(date, time) < NOW()")
        cleanup_db.commit()
        cleanup_cursor.close(); cleanup_db.close()
    except Exception as e:
        print(f"Ride cleanup error: {e}")

scheduler.add_job(func=send_ride_notifications, trigger='interval', seconds=60,
                  id='ride_notification_job', replace_existing=True)
scheduler.add_job(func=cleanup_expired_rides, trigger='interval', seconds=60,
                  id='expired_ride_cleanup_job', replace_existing=True)

if __name__ == "__main__":
    app.run(debug=True)
