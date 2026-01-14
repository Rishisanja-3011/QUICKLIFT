from flask import Flask, render_template, request, redirect
import mysql.connector

app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Patel_2101",
    database="quicklift"
)
cursor = db.cursor()

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        username = request.form['username']
        email = request.form['email']
        contact = request.form['contact']
        city = request.form['city']
        password = request.form['password']
        gender = request.form['gender']
        file = request.files['file']

        file_path = file.filename

        query = """
        INSERT INTO userdata
        (fullname, username, email, phnumber, city, gender, files, passwords)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (fullname, username, email, contact, city, gender, file_path, password)
        cursor.execute(query, values)
        db.commit()

        return redirect('/login')

    return render_template('register.html')

if __name__ == "__main__":
    app.run(debug=True)
