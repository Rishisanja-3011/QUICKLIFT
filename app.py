from flask import Flask, request, redirect, render_template
import mysql.connector
import os

app = Flask(__name__)

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Patel_2101",
    database="quicklift"
)
cursor = db.cursor()

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        query = "SELECT * FROM userdata WHERE username=%s AND passwords=%s"
        values = (username, password)
        cursor.execute(query, values)
        result = cursor.fetchone()
        if result:
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. Collect data from form
        fullname = request.form['fullname']
        username = request.form['username']
        email = request.form['email']
        contact = request.form['contact']
        city = request.form['city']
        password = request.form['password']
        gender = request.form['gender']
        
        # 2. Handle the file
        file = request.files['file']
        if file:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            file_path = file.filename
        else:
            file_path = ""

        # 3. Database logic (MUST BE INDENTED INSIDE THE IF BLOCK)
        query = """INSERT INTO userdata (fullname, username, email, phnumber, city, gender, files, passwords)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        values = (fullname, username, email, contact, city, gender, file_path, password)
        
        cursor.execute(query, values)
        db.commit()

        return redirect('/login')

    # This only runs for GET requests (opening the page)
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

if __name__ == "__main__":
    app.run(debug=True)