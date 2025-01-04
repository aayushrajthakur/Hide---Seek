from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize the Flask application
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:Cliffard06.#@localhost/users'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.secret_key = 'Megatron113.#'

db = SQLAlchemy(app)


# Define User model
class Users(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(20), nullable=False)
    hashed_password = db.Column(db.String(1200), nullable=False)

@app.route('/')
def home():
    return render_template('register.html')

# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = Users.query.filter_by(username=username).first()

        
        if user is not None:  
            if user.hashed_password == password:
                session['username'] = username
                
                return redirect(url_for('main'))
            else:
                flash('Invalid password!','danger')  
        else:
            flash('User does not exists.!','danger') 

        return redirect(url_for('login')) 
    return render_template('login.html')

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        con_password = request.form.get('con_password')

        existing_user = Users.query.filter_by(username=username).first()
        print(f"Existing user: {existing_user}")

        if existing_user:
            flash('Username already exists!','danger')
            return redirect(url_for('register'))

        if password == con_password:
            hashed_password = password
            new_user = Users(username=username, email=email, hashed_password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.','success')
            return redirect(url_for('login'))
        else:
            flash('Passwords do not match!','danger')
            return redirect(url_for('register'))
    return render_template('register.html')

# Route for user homepage
@app.route('/main')
def main():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    else:
        return redirect(url_for('login'))
@app.route('/encode')
def encode():
    return render_template('encode.html')

@app.route('/decode')
def decode():
    return render_template('decode.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

# Main execution block
if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)
        db.create_all()
    