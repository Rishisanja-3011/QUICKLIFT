import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Patel_2101",
    database="quicklift"
)

cursor = db.cursor()

