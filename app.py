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

#login////////

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('login.html',error="All Fields required to be filled ")
        query = "SELECT * FROM userdata WHERE username=%s AND passwords=%s"
        values = (username, password)
        cursor.execute(query, values)
        result = cursor.fetchone()
        if result:
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

#register
#=====================================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. Collect data from form
        fullname = request.form.get('fullname')
        username = request.form.get('username')
        email = request.form.get('email')
        contact = request.form.get('contact')
        city = request.form.get('city')
        password = request.form.get('password')
        gender = request.form.get('gender')
        file = request.files.get('file')
        
        #empty field check
        if not all([fullname, username, email, contact, city, password, gender,file]):
            return render_template('register.html', error="Please fill in all the fields")

        # 2. Handle the file
        
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
#dashboard
#==========================================================
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

if __name__ == "__main__":
    app.run(debug=True)