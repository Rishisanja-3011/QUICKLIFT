import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="preet.347"
)

cursor = db.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS quicklift")
cursor.execute("USE quicklift")

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
    passwords VARCHAR(255)
)""")

# 2. Rides Table (UPDATED to match your app.py)
# Note: We drop it first so we can recreate it with the missing columns
cursor.execute("DROP TABLE IF EXISTS rides") 

query = """CREATE TABLE rides (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

cursor.execute(query)
db.commit()

print("DATABASE UPDATED! Now 'date' and 'leaving_from' columns exist.")

cursor.close()
db.close()