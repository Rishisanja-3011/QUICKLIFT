import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Patel_2101",
    database="quicklift"
)

cursor = db.cursor()

query = """CREATE DATABASE IF NOT EXISTS quicklift"""
cursor.execute(query)
db.commit()

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

print("DATABase banni gyo choduuu")