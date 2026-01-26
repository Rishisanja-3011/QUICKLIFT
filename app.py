from flask import Flask, request, redirect, render_template,url_for,session
from authlib.integrations.flask_client import OAuth
import mysql.connector
import os

app = Flask(__name__)
app.secret_key ="Patelbhai_here_3011"
# Database connection
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='853368867067-agsdp0bjm4c4q56j29pjrppqlh0fff63.apps.googleusercontent.com', # Get this from Google Console
    client_secret='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', # Get this from Google Console
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Patel_2101",
    database="quicklift"
)
cursor = db.cursor()

# Configuration for file uploads
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
# --- GOOGLE AUTH ROUTES ---

@app.route('/login/google')
def google_login():
    # This sends the user to Google's login page
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if user_info:
        session['user'] = user_info
        # Optional: Check if user exists in your MySQL 'userdata' table
        # If not, you could 'INSERT' them here automatically.
        return redirect('/dashboard')
    
    return redirect('/login')

#login////////

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        #validation for empty fields
        if not username or not password:
            return render_template('login.html',error="All Fields required to be filled ")
        query = "SELECT * FROM userdata WHERE username=%s AND passwords=%s"
        values = (username, password)
        cursor.execute(query, values)
        result = cursor.fetchone()
        if result:
            session['user'] = result
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
        confirm_password = request.form.get('confirm_password')
        gender = request.form.get('gender')
        file = request.files.get('file')
        
        #empty field check
        if not all([fullname, username, email, contact, city, password,confirm_password, gender,file]):
            return render_template('register.html', error="Please fill in all the fields")

        #password match check
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")
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
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html',user=session['user'])

if __name__ == "__main__":
    app.run(debug=True)