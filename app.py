from flask import Flask, request, redirect, render_template, url_for, session, flash
from flask_mail import Mail, Message
import random
try:
    from authlib.integrations.flask_client import OAuth
except Exception:
    OAuth = None
import mysql.connector
import os
import requests 
from datetime import datetime, date as dt_date, timedelta
from flask import jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import atexit


app = Flask(__name__)
# Email OTP configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'sanjarishi99@gmail.com'
app.config['MAIL_PASSWORD'] = 'luufzfvkyplvevxo'

mail = Mail(app)
app.secret_key = "Patelbhai_here_3011"
scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())
#Database connection
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
    cursor = db.cursor(dictionary=True,buffered=True)
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
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        response = requests.get(url).json()
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
        cursor.execute("select * from userdata WHERE email=%s",(user_info['email'],))
        db_user = cursor.fetchone()
        if db_user:
            # User exists, use their database record (which has 'username')
            session['user'] = db_user
         
        else:
            # New user: Create a compatible dictionary for the session
            # This prevents the 'username' KeyError in your dashboard logic
            session['user'] = {
                'username': user_info.get('email').split('@')[0], # Fallback username
                'fullname': user_info.get('name'),
                'email': user_info.get('email'),
                'is_google': True
            }
        return redirect('/dashboard')
    return redirect('/login')


@app.route('/forgot-password', methods=['GET','POST'])
def forgot_password():

    if request.method == 'POST':

        email = request.form.get('email')

        cursor.execute("SELECT * FROM userdata WHERE email=%s", (email,))
        user = cursor.fetchone()

        if not user:
            return render_template("forgot-password.html", error="Email not found")

        otp = generate_otp()

        session['otp'] = otp
        session['otp_type'] = "reset"
        session['reset_email'] = email

        send_otp_email(email, otp)

        return render_template("otp.html")

    return render_template("forgot-password.html")


@app.route('/reset-password', methods=['GET','POST'])
def reset_password():

    if request.method == 'POST':

        new_password = request.form.get('password')
        email = session.get('reset_email')

        cursor.execute(
            "UPDATE userdata SET passwords=%s WHERE email=%s",
            (new_password, email)
        )

        db.commit()

        flash("Password updated successfully")
        return redirect('/login')

    return render_template("reset-password.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('login.html', error="All Fields required")
        
        try:
            # Ensure DB is connected
            if not db.is_connected():
                db.reconnect()
            
            # Use the cursor to find the user
            query = "SELECT * FROM userdata WHERE username=%s AND passwords=%s"
            cursor.execute(query, (username, password))
            result = cursor.fetchone() 
            
            if result:
                # result is a dictionary because of cursor(dictionary=True)
                session['user'] = result
                return redirect('/dashboard')
            else:
                return render_template('login.html', error="Invalid username or password")
                
        except Exception as e:
            print(f"Login Error: {e}")
            return render_template('login.html', error="Database connection failed. Please try again.")

    return render_template('login.html')

def send_otp_email(email, otp):
    msg = Message(
        "QuickLift OTP Verification",
        sender=app.config['MAIL_USERNAME'],
        recipients=[email]
    )

    msg.body = f"<-----------QuickLift---------->\n Your OTP for QuickLift verification is: {otp}"

    mail.send(msg)

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

        # Store data temporarily in session
        session['register_data'] = {
            "fullname": fullname,
            "username": username,
            "email": email,
            "contact": contact,
            "city": city,
            "gender": gender,
            "file_path": file_path,
            "password": password
        }
        cursor.execute(
        "SELECT * FROM userdata WHERE username=%s OR email=%s",
        (username,email)
        )

        existing = cursor.fetchone()

        if existing:
            return render_template("register.html",
                           error="Username or email already exists")
        otp = generate_otp()
        session['otp'] = otp
        session['otp_type'] = "register"
        send_otp_email(email, otp)
        return render_template("otp.html")


        # query = """INSERT INTO userdata (fullname, username, email, phnumber, city, gender, files, passwords)
        #            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        # cursor.execute(query, (fullname, username, email, contact, city, gender, file_path, password))
        # db.commit()
        # return redirect('/login')
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    
    user_data = session['user']
    user_name = user_data.get('username') if isinstance(user_data, dict) else user_data[1]
    
    # Auto-delete past rides
    try:
        cursor.execute("DELETE FROM rides WHERE date < CURDATE() OR (date = CURDATE() AND time < CURTIME())")
        db.commit()
    except Exception as e:
        print("Cleanup error:", e)
        db.rollback()
    
    # 1. Fetch live activity for others' rides
    cursor.execute("SELECT * FROM rides WHERE username != %s AND seats > 0 ORDER BY date ASC LIMIT 3", (user_name,))
    recent_rides = cursor.fetchall()
    
    # 2. Intelligence: Calculate CO2 Savings (Real-time)
    # Logic: count how many times this user has booked a ride
    cursor.execute("SELECT COUNT(*) as total FROM bookings WHERE passenger_username = %s", (user_name,))
    booking_count = cursor.fetchone()['total']
    
    # Logic: count how many rides this user has published
    cursor.execute("SELECT COUNT(*) as total FROM rides WHERE username = %s", (user_name,))
    published_count = cursor.fetchone()['total']
    
    # 3. Aggregate Stats
    stats = {
        'co2_saved': round((booking_count + published_count) * 2.15, 1), # 2.15kg per ride avg
        'network_status': "Active" if recent_rides else "Searching",
        'total_rides': booking_count + published_count
    }
    
    return render_template('dashboard.html', user=session['user'], recent_rides=recent_rides, stats=stats)


@app.route('/publish', methods=['GET', 'POST'])
def publish():
    if 'user' not in session: return redirect('/login')
    print("FORM DATA:")
    print(request.form)

    
    if request.method == 'POST':
        start_lat = float(request.form.get('start_lat'))
        start_lon = float(request.form.get('start_lon'))
        dest_lat = float(request.form.get('dest_lat'))
        dest_lon = float(request.form.get('dest_lon'))
        leaving_from = request.form.get('leaving_from')
        going_to = request.form.get('going_to')
        date = request.form.get('date')
        time = request.form.get('time')
        seats = int(request.form.get('seats', '1'))
        manual_price = request.form.get('manual_price')
        vehicle = request.form.get('vehicle')
        
        # Validating date limits
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d').date()
            today = dt_date.today()
            if parsed_date < today:
                flash("Cannot publish rides in the past.", "error")
                return redirect('/publish')
            if parsed_date > today + timedelta(days=15):
                flash("Cannot publish rides more than 15 days in advance.", "error")
                return redirect('/publish')
        except Exception as e:
            pass # format error handling handled differently or ignored here
        
        km = get_road_distance(start_lat, start_lon, dest_lat, dest_lon)
        total_price = 40 + (km * 12)
        price_per_seat = round(total_price / max(seats, 1), 2)
       
        
        try:
            query = "INSERT INTO rides (username, leaving_from, going_to, date, time, seats, vehicle, distance_km, price_per_seat, total_price) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            user_data = session['user']
            if isinstance(user_data, dict):
                user_name=user_data.get('username') or user_data.get('email')

            else:

             user_data[1]
            
            cursor.execute(query, (user_name, leaving_from, going_to, date, time, seats, vehicle, km, price_per_seat, round(total_price, 2)))
            db.commit()
            flash("Ride published successfully!", "success")
        except Exception as e:
          print("INSERT FAILED:")
          print (str(e))
        


        return render_template(
            'publish.html', 
            user=session['user'], 
            calculated_km=km, 
            total_price=round(total_price, 2), 
            price_per_seat=price_per_seat
        )

    return render_template('publish.html', user=session['user'])

@app.route('/find-ride', methods=['GET', 'POST'])
def find_ride():
    if 'user' not in session: return redirect('/login')
    
    # Auto-delete past rides
    try:
        cursor.execute("DELETE FROM rides WHERE date < CURDATE() OR (date = CURDATE() AND time < CURTIME())")
        db.commit()
    except Exception as e:
        print("Cleanup error:", e)
        db.rollback()

    rides = []
    if request.method == 'POST':
        leaving_from = request.form.get('from')
        going_to = request.form.get('to')
        ride_date = request.form.get('date')
        
        if ride_date:
            query = "SELECT * FROM rides WHERE leaving_from LIKE %s AND going_to LIKE %s AND date = %s AND seats > 0 ORDER BY date ASC"
            cursor.execute(query, (f"%{leaving_from}%", f"%{going_to}%", ride_date))
        else:
            query = "SELECT * FROM rides WHERE leaving_from LIKE %s AND going_to LIKE %s AND seats > 0 ORDER BY date ASC"
            cursor.execute(query, (f"%{leaving_from}%", f"%{going_to}%"))
        rides = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM rides WHERE seats > 0 ORDER BY date ASC")
        rides = cursor.fetchall()

    return render_template('findride.html', user=session['user'], rides=rides)

@app.route('/reserve/<int:ride_id>')
def reserve_page(ride_id):
    if 'user' not in session: return redirect('/login')
    
    query = "SELECT * FROM rides WHERE id = %s"
    cursor.execute(query, (ride_id,))
    ride = cursor.fetchone()
    
    if not ride:
        flash("Ride not found!")
        return redirect('/find-ride')
        
    return render_template('reserve.html', user=session['user'], ride=ride)

@app.route('/book-ride/<int:ride_id>')
def book_ride(ride_id):
    if 'user' not in session:
        return redirect('/login')

    user_data = session['user']
    user_name = user_data['username'] if isinstance(user_data, dict) else user_data[1]

    if not db.is_connected():
        db.reconnect()

    cursor.execute("SELECT username, seats FROM rides WHERE id = %s", (ride_id,))
    ride = cursor.fetchone()

    if ride and ride['seats'] > 0:
        if ride['username'] == user_name:
            flash("You cannot book your own ride.")
            return redirect('/find-ride')

        try:
            cursor.execute("UPDATE rides SET seats = seats - 1 WHERE id = %s", (ride_id,))
            cursor.execute(
                "INSERT INTO bookings (ride_id, passenger_username) VALUES (%s, %s)",
                (ride_id, user_name)
            )
            db.commit()
            flash("Booking Successful! Track your driver below.", "success")
            # ← Now redirects to live tracking page instead of insights
            return redirect(f'/track/{ride_id}')
        except Exception as e:
            db.rollback()
            print(f"Sync Error: {e}")
            return "Database Sync Error", 500

    flash("Sorry, no seats left for this ride.")
    return redirect('/find-ride')


@app.route('/insights')
def insights():
    if 'user' not in session: return redirect('/login')
    
    user_data = session['user']
    user_name = user_data['username'] if isinstance(user_data, dict) else user_data[1]

    # Join the bookings ledger with the rides table to get full trip details
    query = """
        SELECT r.leaving_from, r.going_to, r.date, r.price_per_seat, b.status 
        FROM bookings b 
        JOIN rides r ON b.ride_id = r.id 
        WHERE b.passenger_username = %s
        ORDER BY b.booking_date DESC
    """
    cursor.execute(query, (user_name,))
    history = cursor.fetchall()

    # Calculate real-time stats
    stats = {
        'carbon_saved': round(len(history) * 2.15, 2), # Estimated kg saved
        'wallet_balance': 2450.00, # Placeholder for now
        'total_rides': len(history)
    }
    
    return render_template('insights.html', user=session['user'], history=history, stats=stats)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

def generate_otp():
    return str(random.randint(100000, 999999))


@app.route('/verify-otp', methods=['POST'])
def verify_otp():

    user_otp = request.form.get('otp')

    if user_otp == session.get('otp'):

        if session.get('otp_type') == "register":

            data = session.get('register_data')

            query = """INSERT INTO userdata 
            (fullname, username, email, phnumber, city, gender, files, passwords)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""

            cursor.execute(query, (
                data['fullname'],
                data['username'],
                data['email'],
                data['contact'],
                data['city'],
                data['gender'],
                data['file_path'],
                data['password']
            ))

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
    
@app.route('/update-location', methods=['POST'])
def update_location():
    """Driver's browser calls this every 5 seconds with their GPS coords."""
    if 'user' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')
    user_data = session['user']
    username = user_data.get('username') if isinstance(user_data, dict) else user_data[1]

    try:
        if not db.is_connected():
            db.reconnect()
        # Upsert: update if exists, insert if not
        cursor.execute("""
            INSERT INTO user_locations (username, latitude, longitude)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE latitude=%s, longitude=%s, updated_at=NOW()
        """, (username, lat, lon, lat, lon))
        db.commit()
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Location update error: {e}")
        return jsonify({'error': str(e)}), 500
@app.route('/get-location/<int:ride_id>')
def get_location(ride_id):
    """Returns the driver's latest GPS coords for a given ride."""
    if 'user' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    try:
        if not db.is_connected():
            db.reconnect()
        # Get the driver's username from the ride
        cursor.execute("SELECT username FROM rides WHERE id = %s", (ride_id,))
        ride = cursor.fetchone()
        if not ride:
            return jsonify({'error': 'ride not found'}), 404

        driver_username = ride['username']

        # Get their latest location
        cursor.execute("""
            SELECT latitude, longitude, updated_at
            FROM user_locations
            WHERE username = %s
        """, (driver_username,))
        loc = cursor.fetchone()

        if loc and loc['latitude']:
            return jsonify({
                'lat': loc['latitude'],
                'lon': loc['longitude'],
                'updated_at': str(loc['updated_at'])
            })
        else:
            return jsonify({'error': 'location not available yet'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/track/<int:ride_id>')
def track_ride(ride_id):
    """Live tracking page for the passenger."""
    if 'user' not in session:
        return redirect('/login')

    try:
        if not db.is_connected():
            db.reconnect()

        cursor.execute("SELECT * FROM rides WHERE id = %s", (ride_id,))
        ride = cursor.fetchone()
        if not ride:
            flash("Ride not found.")
            return redirect('/insights')

        # Get driver's phone number for the contact info
        cursor.execute("SELECT phnumber, fullname FROM userdata WHERE username = %s", (ride['username'],))
        driver = cursor.fetchone()

        return render_template('tracking.html',
                               user=session['user'],
                               ride=ride,
                               driver=driver,
                               ride_id=ride_id)
    except Exception as e:
        print(f"Track error: {e}")
        return redirect('/insights')
def send_ride_notifications():
    """
    Runs every minute. Finds rides departing in the next 5 minutes
    and emails each booked passenger with driver location + phone.
    """
    try:
        # Create a fresh connection for the scheduler thread
        notif_db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Patel_2101",
            database="quicklift"
        )
        notif_cursor = notif_db.cursor(dictionary=True)

        # Find rides departing in 4–6 minutes from now (5-min window)
        notif_cursor.execute("""
            SELECT r.id, r.username, r.leaving_from, r.going_to, r.date, r.time,
                   u.phnumber, u.fullname,
                   ul.latitude, ul.longitude
            FROM rides r
            JOIN userdata u ON r.username = u.username
            LEFT JOIN user_locations ul ON r.username = ul.username
            WHERE r.date = CURDATE()
              AND r.time BETWEEN ADDTIME(CURTIME(), '00:04:00')
                             AND ADDTIME(CURTIME(), '00:06:00')
        """)
        upcoming_rides = notif_cursor.fetchall()

        for ride in upcoming_rides:
            # Get all passengers booked on this ride
            notif_cursor.execute("""
                SELECT b.passenger_username, u.email, u.fullname
                FROM bookings b
                JOIN userdata u ON b.passenger_username = u.username
                WHERE b.ride_id = %s AND b.status = 'Booked'
            """, (ride['id'],))
            passengers = notif_cursor.fetchall()

            # Build Google Maps link for driver location
            if ride['latitude'] and ride['longitude']:
                maps_link = f"https://www.google.com/maps?q={ride['latitude']},{ride['longitude']}"
                location_text = f"Driver's current location: {maps_link}"
            else:
                maps_link = None
                location_text = "Driver location not available yet. Please contact them directly."

            # Send email to each passenger
            for passenger in passengers:
                try:
                    msg = Message(
                        subject="🚗 QuickLift — Your ride departs in 5 minutes!",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[passenger['email']]
                    )
                    msg.body = f"""
<----------- QuickLift ----------->

Hi {passenger['fullname']},

Your ride is departing in approximately 5 minutes!

RIDE DETAILS:
  From  : {ride['leaving_from']}
  To    : {ride['going_to']}
  Driver: {ride['fullname']} (@{ride['username']})

CONTACT YOUR DRIVER:
  Phone : {ride['phnumber']}

{location_text}

You can also track live on QuickLift:
  http://127.0.0.1:5000/track/{ride['id']}

Safe travels!
— QuickLift Team
"""
                    with app.app_context():
                        mail.send(msg)
                    print(f"Notification sent to {passenger['email']} for ride {ride['id']}")
                except Exception as e:
                    print(f"Email send error for {passenger['email']}: {e}")

        notif_cursor.close()
        notif_db.close()

    except Exception as e:
        print(f"Scheduler error: {e}")
        # Register the job — runs every 60 seconds
scheduler.add_job(
    func=send_ride_notifications,
    trigger='interval',
    seconds=60,
    id='ride_notification_job',
    replace_existing=True
)


if __name__ == "__main__":
    app.run(debug=True)