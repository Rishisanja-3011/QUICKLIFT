import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Patel_2101"
)

cursor = db.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS quicklift")
cursor.execute("USE quicklift")

def add_column_if_missing(table_name, column_definition):
    try:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
    except mysql.connector.Error as err:
        if err.errno != 1060:
            raise

# 1. User Table (Stays the same)
cursor.execute("""CREATE TABLE IF NOT EXISTS userdata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fullname VARCHAR(100),
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100),
    phnumber VARCHAR(20),
    city VARCHAR(50),
    gender VARCHAR(10),
    files VARCHAR(255),
    id_file VARCHAR(255),
    passwords VARCHAR(255)
)""")


# 2. Rides Table (UPDATED to match your app.py)
# Note: We drop it first so we can recreate it with the missing columns
# cursor.execute("DROP TABLE IF EXISTS rides") 

query = """CREATE TABLE IF NOT EXISTS  rides (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255),
    leaving_from VARCHAR(255),
    going_to VARCHAR(255),
    date DATE,
    time TIME,
    seats INT,
    vehicle VARCHAR(100),
    distance_km DECIMAL(10,2),
    price_per_seat DECIMAL(10,2),
    total_price DECIMAL(10,2),
    route_geojson MEDIUMTEXT,
    duration_minutes INT,
    reminder_sent TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""
cursor.execute(query)

cursor.execute("""
CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ride_id INT,
    passenger_username VARCHAR(255),
    pickup_stop_id INT NULL,
    drop_stop_id INT NULL,
    pickup_name VARCHAR(255) NULL,
    drop_name VARCHAR(255) NULL,
    segment_distance_km DECIMAL(10,2) NULL,
    booked_price DECIMAL(10,2) NULL,
    status VARCHAR(50) DEFAULT 'Booked',
    booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_locations (
    username VARCHAR(255) PRIMARY KEY,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
)""")

cursor.execute("""
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

cursor.execute("""
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

try:
    cursor.execute("ALTER TABLE rides ADD COLUMN reminder_sent TINYINT(1) NOT NULL DEFAULT 0")
except mysql.connector.Error as err:
    if err.errno != 1060:
        raise

add_column_if_missing("rides", "route_geojson MEDIUMTEXT NULL")
add_column_if_missing("rides", "duration_minutes INT NULL")
add_column_if_missing("userdata", "id_file VARCHAR(255) NULL")
add_column_if_missing("bookings", "pickup_stop_id INT NULL")
add_column_if_missing("bookings", "drop_stop_id INT NULL")
add_column_if_missing("bookings", "pickup_name VARCHAR(255) NULL")
add_column_if_missing("bookings", "drop_name VARCHAR(255) NULL")
add_column_if_missing("bookings", "segment_distance_km DECIMAL(10,2) NULL")
add_column_if_missing("bookings", "booked_price DECIMAL(10,2) NULL")

db.commit()


print("DATABASE UPDATED! Multi-stop route tables and booking segment columns exist.")

cursor.close()
db.close()
