import base64
import io
from flask import Flask, render_template, request, redirect, send_file, url_for, session, flash
from PIL import Image  
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:Cliffard06.#@localhost/users'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = 'static/uploads'


app.secret_key = 'Megatron113.#'

db = SQLAlchemy(app)


class Users(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(20), nullable=False)
    hashed_password = db.Column(db.String(1200), nullable=False)

@app.route('/')
def home():
    return render_template('register.html')


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


@app.route('/main')
def main():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    else:
        return redirect(url_for('login'))
    
@app.route('/encode', methods=['GET', 'POST'])
def encode():
    if request.method == 'POST':
        img = request.files['image']
        message = request.form.get('message')
        password = request.form.get('password')
        
        if img.filename == '':
            flash('No selected file!','danger')
            return redirect(url_for('encode'))

        if img:
            filename = secure_filename(img.filename) 
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) 

            img.save(img_path) 
            img = Image.open(img_path)  
            encoded_img = img.copy()  

            width, height = img.size
            message += '\0'  
            message_bits = ''.join([format(ord(char), '08b') for char in message])
            message_index = 0

            for y in range(height):
                for x in range(width):
                    pixel = list(img.getpixel((x, y)))
                    for n in range(3):  
                        if message_index < len(message_bits):
                            pixel[n] = pixel[n] & ~1 | int(message_bits[message_index])
                            message_index += 1
                    encoded_img.putpixel((x, y), tuple(pixel))
                    if message_index >= len(message_bits):
                        break
                if message_index >= len(message_bits):
                    break
            encoded_filename = f"encoded_{filename}"
            filename = secure_filename(encoded_filename)
            output_path = os.path.join(app.config['UPLOAD_FOLDER'],filename)
            encoded_img.save(output_path) 

            #Encode the image to base64
            image_01 = Image.open(output_path)
            buffered = io.BytesIO()
            image_01.save(buffered, format="PNG")
            encoded_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

            session['encoded_filepath'] = output_path
            return redirect(url_for('download_image'))
        return 'No image uploaded', 400
        
    return render_template('encode.html')


@app.route('/download_image', methods=['GET'])
def download_image():
    encoded_filepath = session.get('encoded_filepath')

    if encoded_filepath and os.path.exists(encoded_filepath):
        return send_file(
            encoded_filepath,
            as_attachment=True,
            download_name='encoded_image.png',
            mimetype='image/png'
        )
    return 'No image available for download', 404


@app.route('/decode')
def decode():
    return render_template('decode.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')


if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)
        db.create_all()
    