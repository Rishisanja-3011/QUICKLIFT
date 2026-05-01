# QuickLift

QuickLift is a Flask-based peer-to-peer ride sharing web application. It lets users register with OTP verification, publish upcoming rides, search and reserve available seats, track driver location in real time, and manage ride activity from an insights dashboard.

The project is built as a Python Flask app with MySQL for persistence and HTML/CSS/JavaScript templates for the user interface.

## Features

- User registration with profile photo and ID proof upload
- Email OTP verification for registration and password reset
- Username/password login
- Optional Google OAuth login
- Dashboard with recent rides, ride counts, and estimated CO2 savings
- Ride publishing with city autocomplete, route distance calculation, and automatic price calculation
- Ride search by origin, destination, and optional travel date
- Seat booking with automatic seat count updates
- Passenger ride cancellation and seat release
- Driver ride cancellation with passenger email notifications
- Live driver location sharing and passenger tracking map
- Ride insights page for bookings and published rides
- Passenger list view for ride publishers
- User profile viewing and editing
- Background scheduler for ride reminder emails

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python, Flask |
| Database | MySQL |
| Email | Flask-Mail with Gmail SMTP |
| Authentication | Flask sessions, Authlib Google OAuth |
| Scheduling | APScheduler |
| Mapping and location | Browser Geolocation API, Leaflet, OpenStreetMap/CARTO tiles |
| Route distance | OSRM public route API |
| City search | Nominatim and Photon APIs |
| Frontend | HTML, CSS, JavaScript, Jinja templates |

## Project Structure

```text
QUICKLIFT/
+-- app.py                  # Main Flask application and routes
+-- database/
|   +-- database.py         # MySQL database bootstrap script
+-- static/
|   +-- main.js             # Frontend script experiments/helpers
|   +-- style.css           # Main application styling
+-- templates/
|   +-- dashboard.html
|   +-- findride.html
|   +-- forgot-password.html
|   +-- index.html
|   +-- insights.html
|   +-- login.html
|   +-- otp.html
|   +-- profile.html
|   +-- publish.html
|   +-- register.html
|   +-- reserve.html
|   +-- reset-password.html
|   +-- ride_passengers.html
|   +-- tracking.html
+-- uploads/                # Uploaded profile photos, ID files, and test assets
```

## Prerequisites

Install these before running the project:

- Python 3.10 or newer
- MySQL Server
- A Gmail account with an app password for SMTP email
- Optional: Google Cloud OAuth credentials for Google login

## Python Dependencies

Install the Python dependencies from `requirements.txt`:

```powershell
py -m pip install -r requirements.txt
```

If you prefer using a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

The dependency file includes Flask, Flask-Mail, Authlib, MySQL Connector, Requests, and APScheduler.

## Configuration

The current code stores configuration directly in `app.py` and `database/database.py`. Before running the project on a new machine, update these values.

### Database Configuration

In `app.py`:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_mysql_password",
    "database": "quicklift"
}
```

In `database/database.py`:

```python
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="your_mysql_password"
)
```

### Email Configuration

In `app.py`, update the Gmail SMTP settings:

```python
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_gmail_app_password'
```

Use a Gmail app password, not your normal Gmail password.

### Google OAuth Configuration

Google login is optional. If you want to use it, create OAuth credentials in Google Cloud Console and update:

```python
client_id='your_google_client_id'
client_secret='your_google_client_secret'
```

For local development, add this redirect URI to your Google OAuth client:

```text
http://127.0.0.1:5000/auth/google/callback
```

## Database Setup

Run the bootstrap script:

```powershell
py database\database.py
```

The app expects the `quicklift` database and these main tables:

- `userdata`
- `rides`
- `bookings`
- `user_locations`

Important: `database/database.py` creates the base database, `userdata`, `rides`, and `bookings`, but the current application also expects `userdata.id_file` and the `user_locations` table. If they do not exist, run these SQL statements in MySQL:

```sql
USE quicklift;

ALTER TABLE userdata
ADD COLUMN id_file VARCHAR(255) AFTER files;

CREATE TABLE IF NOT EXISTS user_locations (
    username VARCHAR(255) PRIMARY KEY,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);
```

If the `id_file` column already exists, MySQL may show a duplicate column error. That is safe to ignore.

## Running the Application

Start the Flask server:

```powershell
py app.py
```

Open the app in your browser:

```text
http://127.0.0.1:5000
```

When the app starts:

- Logged-out users are redirected to `/register`
- Logged-in users are redirected to `/dashboard`
- Uploaded files are stored in the `uploads/` folder

## Main Routes

| Route | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Redirects users based on login status |
| `/register` | GET, POST | Creates a new account and sends OTP |
| `/verify-otp` | POST | Verifies registration or reset OTP |
| `/login` | GET, POST | Logs in with username and password |
| `/login/google` | GET | Starts Google OAuth login |
| `/auth/google/callback` | GET | Handles Google OAuth callback |
| `/forgot-password` | GET, POST | Sends reset OTP |
| `/reset-password` | GET, POST | Updates password after OTP verification |
| `/logout` | GET | Ends the session |
| `/dashboard` | GET | Shows account summary and recent rides |
| `/publish` | GET, POST | Publishes a new ride |
| `/find-ride` | GET, POST | Searches available rides |
| `/reserve/<ride_id>` | GET | Shows ride reservation details |
| `/book-ride/<ride_id>` | GET | Books a seat on a ride |
| `/track/<ride_id>` | GET | Shows live driver tracking |
| `/update-location` | POST | Saves the current user's GPS location |
| `/get-location/<ride_id>` | GET | Returns the driver's latest location |
| `/check-ride/<ride_id>` | GET | Checks if a ride still exists |
| `/insights` | GET | Shows bookings and published rides |
| `/unbook/<booking_id>` | POST | Cancels a passenger booking |
| `/cancel-ride/<ride_id>` | POST | Cancels a driver's published ride |
| `/ride-passengers/<ride_id>` | GET | Shows passengers for a published ride |
| `/profile/<username>` | GET | Shows a user's profile |
| `/edit-profile` | POST | Updates profile information |

## How Ride Publishing Works

1. The driver enters origin, destination, date, time, vehicle, and seats.
2. The frontend uses city search APIs to find coordinates.
3. The backend calls OSRM to calculate road distance.
4. The app calculates pricing with:

```text
total_price = 40 + (distance_km * 12)
price_per_seat = total_price / available_seats
```

5. The ride is saved in MySQL and becomes searchable by passengers.

Rides can only be published from the current date up to 15 days ahead.

## Live Tracking

QuickLift uses browser geolocation to share driver location:

- The dashboard sends a passive location beacon every 10 seconds.
- The tracking page updates the driver marker every 5 seconds.
- Passengers can open the driver's latest location in Google Maps.
- Location sharing requires browser permission.

For production deployments, geolocation works best over HTTPS. Some browsers block or restrict location permissions on insecure origins.

## Email Notifications

Email is used for:

- Registration OTP
- Password reset OTP
- Ride cancellation notifications
- Ride departure reminders

The background scheduler runs every 60 seconds and sends reminder emails for rides departing in about 5 minutes.

## Uploaded Files

User-uploaded profile photos and ID files are stored in:

```text
uploads/
```

The app serves uploaded files through:

```text
/uploads/<filename>
```

For a production app, uploaded filenames should be sanitized and files should be stored in private object storage or a protected folder.

## Security Notes

Before sharing or deploying this project, review these items:

- Move database passwords, Gmail credentials, OAuth secrets, and Flask secret key into environment variables.
- Rotate any credentials that were committed into the repository.
- Hash user passwords instead of storing plain text passwords.
- Validate and sanitize uploaded files and filenames.
- Restrict upload file types and file sizes.
- Add CSRF protection for forms.
- Use HTTPS in production.
- Avoid exposing uploaded ID proof files publicly.
- Replace debug mode with a production WSGI server for deployment.

## Troubleshooting

### Database connection fails

Check that MySQL is running and that `DB_CONFIG` in `app.py` matches your local MySQL username and password.

### Registration fails with an unknown `id_file` column

Add the missing column:

```sql
ALTER TABLE userdata ADD COLUMN id_file VARCHAR(255) AFTER files;
```

### Live tracking fails with `user_locations` errors

Create the missing table:

```sql
CREATE TABLE IF NOT EXISTS user_locations (
    username VARCHAR(255) PRIMARY KEY,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);
```

### OTP email is not sent

Check:

- Gmail SMTP settings
- Gmail app password
- Internet connection
- Whether the Gmail account has security restrictions

### Google login does not work

Check:

- `Authlib` is installed
- Client ID and client secret are correct
- Redirect URI is configured in Google Cloud Console
- The local callback URL is `http://127.0.0.1:5000/auth/google/callback`

## Suggested Future Improvements

- Add a `requirements.txt` file
- Move configuration to `.env` variables
- Add password hashing with Werkzeug or bcrypt
- Add database migrations instead of manual SQL changes
- Add server-side upload validation
- Add tests for authentication, booking, and ride cancellation
- Add admin review for uploaded ID proof files
- Add payment or payment-status support if real ride payments are planned

## License

No license file is currently included in this repository. Add one before distributing or publishing the project.
