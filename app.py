from flask import Flask, request, redirect, render_template, url_for, session
try:
    from authlib.integrations.flask_client import OAuth
except Exception:
    OAuth = None
import mysql.connector
import os
import requests  # Required for calling the Distance API

app = Flask(__name__)
app.secret_key = "Patelbhai_here_3011"

# Database connection
oauth = OAuth(app) if OAuth else None
google = oauth.register(
    name='google',
    client_id='853368867067-agsdp0bjm4c4q56j29pjrppqlh0fff63.apps.googleusercontent.com',
    client_secret='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',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
) if oauth else None

# Database connection with error handling
try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Patel_2101",
        database="quicklift"
    )
    cursor = db.cursor()
    print("Database connected successfully!")
except mysql.connector.Error as err:
    print(f"Database connection error: {err}")
    cursor = None

# Configuration for file uploads
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --- DISTANCE & PRICE LOGIC ---

def get_road_distance(lat1, lon1, lat2, lon2):
    """Calculates road distance using OSRM API."""
    # OSRM expects coordinates in {longitude,latitude} format
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        response = requests.get(url).json()
        # Distance is returned in meters; convert to km
        distance_km = response['routes'][0]['distance'] / 1000
        return round(distance_km, 2)
    except Exception as e:
        print(f"Distance calculation error: {e}")
        return 0

# --- ROUTES ---

@app.route('/')
def index():
    if 'user' in session:
        return redirect('/dashboard')
    return redirect('/register')

@app.route('/login/google')
def google_login():
    if not google: return redirect('/login')
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    if not google: return redirect('/login')
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    if user_info:
        session['user'] = user_info
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('login.html', error="All Fields required")
        query = "SELECT * FROM userdata WHERE username=%s AND passwords=%s"
        cursor.execute(query, (username, password))
        result = cursor.fetchone() 
        if result:
            session['user'] = result
            return redirect('/dashboard')
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        username = request.form.get('username')
        email = request.form.get('email')
        contact = request.form.get('contact')
        city = request.form.get('city')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        gender = request.form.get('gender')
        file = request.files.get('file')
        
        if not all([fullname, username, email, contact, city, password, confirm_password, gender, file]):
            return render_template('register.html', error="Please fill in all fields")

        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")
        
        file_path = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_path))

        query = """INSERT INTO userdata (fullname, username, email, phnumber, city, gender, files, passwords)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (fullname, username, email, contact, city, gender, file_path, password))
        db.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    return render_template('dashboard.html', user=session['user'])

@app.route('/publish', methods=['GET', 'POST'])
def publish():
    if 'user' not in session: return redirect('/login')
    
    if request.method == 'POST':
        # Get data from HTML form
        start_lat = float(request.form.get('start_lat'))
        start_lon = float(request.form.get('start_lon'))
        dest_lat = float(request.form.get('dest_lat'))
        dest_lon = float(request.form.get('dest_lon'))
        leaving_from = request.form.get('leaving_from')
        going_to = request.form.get('going_to')
        date = request.form.get('date')
        time = request.form.get('time')
        seats = int(request.form.get('seats', '1'))
        manual_price = request.form.get('manual_price')  # optional
        vehicle = request.form.get('vehicle')
        notes = request.form.get('notes')
        prefs = {
            'luggage': bool(request.form.get('luggage')),
            'no_smoking': bool(request.form.get('no_smoking')),
            'women_only': bool(request.form.get('women_only')),
        }
        
        # 1. Calculate Distance
        km = get_road_distance(start_lat, start_lon, dest_lat, dest_lon)
        
        # 2. Calculate Price (e.g., 40 base + 12 per km)
        total_price = 40 + (km * 12)
        price_per_seat = round(total_price / max(seats, 1), 2)
        if manual_price:
            try:
                price_per_seat = float(manual_price)
                total_price = round(price_per_seat * seats, 2)
            except ValueError:
                pass
        
        # 3. Store in Database
        try:
            query = "INSERT INTO rides (username, leaving_from, going_to, date, time, seats, vehicle, distance_km, price_per_seat, total_price) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            # Accessing username from session (assuming result[1] is username)
            user_name = session['user'][1] if isinstance(session['user'], list) else session['user'].get('email')
            cursor.execute(query, (user_name, leaving_from, going_to, date, time, seats, vehicle, km, price_per_seat, round(total_price, 2)))
            db.commit()
        except Exception as e:
            print(f"DB Error: {e}")

        return render_template(
            'publish.html',
            user=session['user'],
            calculated_km=km,
            total_price=round(total_price, 2),
            price_per_seat=price_per_seat,
            leaving_from=leaving_from,
            going_to=going_to,
            date=date,
            time=time,
            seats=seats,
            vehicle=vehicle,
            notes=notes,
            prefs=prefs,
            start_lat=start_lat,
            start_lon=start_lon,
            dest_lat=dest_lat,
            dest_lon=dest_lon
        )

    return render_template('publish.html', user=session['user'])

@app.route('/find-ride')
def find_ride():
    if 'user' not in session: return redirect('/login')
    return render_template('findride.html', user=session['user'])

@app.route('/otp')
def otp(): return render_template('otp.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot-password.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

if __name__ == "__main__":
    app.run(debug=True)
