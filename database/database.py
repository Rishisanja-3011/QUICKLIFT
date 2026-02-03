import mysql.connector

# Initial connection to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="preet.347"
)

cursor = db.cursor()

# 1. Create the Database if it doesn't exist
query = """CREATE DATABASE IF NOT EXISTS quicklift"""
cursor.execute(query)
db.commit()

# Switch to the quicklift database
cursor.execute("USE quicklift")

# 2. Create the User Table
query = """CREATE TABLE IF NOT EXISTS userdata (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fullname VARCHAR(100),
            username VARCHAR(50) UNIQUE,
            email VARCHAR(100),
            phnumber VARCHAR(20),
            city VARCHAR(50),
            gender VARCHAR(10),
            files VARCHAR(255),
            passwords VARCHAR(255)
        )"""
cursor.execute(query)
db.commit()

# 3. Create the Rides Table
# This table stores the distance-based pricing results
query = """CREATE TABLE IF NOT EXISTS rides (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255),
            distance_km DECIMAL(10,2),
            price DECIMAL(10,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
cursor.execute(query)
db.commit()

print("DATABASE BAAN K TAYAR HO CHUKAA HEE , KRUPIYA SQL WORKBENCH MEIN JAA K CHECK KAREIN")

# Close the connection
cursor.close()
db.close()