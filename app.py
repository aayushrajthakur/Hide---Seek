import glob
import logging 
from flask import Flask, render_template, request, redirect, send_file, url_for, session, flash
from PIL import Image
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Cliffard06.#@localhost/users'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = 'static/uploads'

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default-dev-key')

db = SQLAlchemy(app)

class Users(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(20), nullable=False)
    hashed_password = db.Column(db.String(1200), nullable=False)

@app.route('/')
def index():
    return render_template('index.html')

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

        if existing_user:
            flash('Username already exists!','danger')
            return redirect(url_for('register'))

        if password == con_password:
            password = password.strip()
            if len(password) < 8:
                flash('Password must be at least 8 characters long!', 'danger')
                return redirect(url_for('register'))
            
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

@app.route('/clean_folder')
def clean_folder(folder_path):
    files = glob.glob(os.path.join(folder_path, '*'))
    
    
    for file in files:
        try:
            if os.path.isfile(file):
                os.remove(file) 
            elif os.path.isdir(file):
                os.rmdir(file) 
        except Exception as e:
            print(f'Error deleting {file}: {e}')


@app.route('/main')
def main():
    if 'username' in session:
        clean_folder('static/encoded_image')
        clean_folder('static/logo_output')
        clean_folder('static/uploads')

        return render_template('home.html', username=session['username'])
    else:
        return redirect(url_for('login'))


def overlay_logo(target_image_path, logo_scale=0.2):
    logo_image_path = 'static/logo.png'
    output_path = 'static/logo_output/output_with_logo.png'

    target_image = Image.open(target_image_path)
    target_width, target_height = target_image.size

    logo_image = Image.open(logo_image_path)
    
    logo_width = int(target_width * logo_scale)
    logo_height = int(logo_width * (logo_image.height / logo_image.width))
    logo_image = logo_image.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

    position = (
        target_width - logo_width - 10, 
        target_height - logo_height - 10
    )
    target_image.paste(logo_image, position, logo_image)

    target_image.save(output_path)
    return output_path

@app.route('/encode_image')
def encode_image(image_path, message, password=None):
    output_path = 'static/encoded_image/result.png'
    image = Image.open(image_path)
    encoded_image = image.copy()
    width, height = image.size
    
    # Combine password and message if password exists
    if password:
        full_message = f"PASSWORD:{password}||MESSAGE:{message}\0"
    else:
        full_message = f"MESSAGE:{message}\0"
        
    message_bits = ''.join([format(ord(char), '08b') for char in full_message])
    message_index = 0

    for y in range(height):
        for x in range(width):
            pixel = list(image.getpixel((x, y)))
            for n in range(3): 
                if message_index < len(message_bits):
                    pixel[n] = pixel[n] & ~1 | int(message_bits[message_index])
                    message_index += 1
            encoded_image.putpixel((x, y), tuple(pixel))
            if message_index >= len(message_bits):
                break
        if message_index >= len(message_bits):
            break

    encoded_image.save(output_path)
    return output_path

@app.route('/encode', methods=['GET', 'POST'])
def encode():
    if 'username' not in session:
        flash('You need to be logged in to encode messages!', 'warning')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        image = request.files.get('image')
        message = request.form.get('message')
        password = request.form.get('password')

        if image is None or image.filename == '':
            flash('No selected file!', 'danger')
            return redirect(url_for('encode'))
        
        try:
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            filename = secure_filename(image.filename)
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(img_path)

            image_with_logo_path = overlay_logo(img_path)
            
            # Pass the password to encode_image
            encoded_image = encode_image(image_with_logo_path, message, password)

            session['encoded_filepath'] = encoded_image

            return redirect(url_for('download_image'))

        except Exception as e:
            logging.error(f"Error occurred while processing the image: {str(e)}")
            flash(f'Error occurred while processing the image: {str(e)}. Please check the file format and try again.', 'danger')
            return redirect(url_for('encode'))

    return render_template('encode.html')

@app.route('/download_image', methods=['GET'])
def download_image():
    encoded_filepath = session.get('encoded_filepath')

    if encoded_filepath and os.path.exists(encoded_filepath):
        flash("Image encoded successfully.")
        return send_file(
            encoded_filepath,
            as_attachment=True,
            mimetype='image/png'
        )
    return 'No image available for download', 404

@app.route('/decoded_message')
def decoded_image(image_path, password=None):
    image = Image.open(image_path)
    width, height = image.size
    message_bits = []
    
    for y in range(height):
        for x in range(width):
            pixel = list(image.getpixel((x, y)))
            for n in range(3):
                message_bits.append(pixel[n] & 1)
    
    message_bytes = [message_bits[i:i+8] for i in range(0, len(message_bits), 8)]
    full_message = ''.join([chr(int(''.join(map(str, byte)), 2)) for byte in message_bytes])
    full_message = full_message.split('\0')[0]  # Split at the null character
    
    # Check if message contains password
    if full_message.startswith("PASSWORD:"):
        parts = full_message.split("||")
        stored_password = parts[0].replace("PASSWORD:", "")
        
        if password is None:
            return None, "This message is password protected. Please provide a password."
        
        if stored_password != password:
            return None, "Incorrect password!"
            
        message = parts[1].replace("MESSAGE:", "")
        return message, None
    else:
        # No password protection
        message = full_message.replace("MESSAGE:", "")
        return message, None

@app.route('/check_password_protection', methods=['POST'])
def check_password_protection():
    if 'username' not in session:
        return {'error': 'Authentication required'}, 401
        
    if 'image' not in request.files:
        return {'error': 'No image file'}, 400
        
    img = request.files['image']
    if img.filename == '':
        return {'error': 'No selected file'}, 400
    
    try:
        filename = secure_filename(img.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        img.save(image_path)
        
        # Check if message is password protected without decoding it
        image = Image.open(image_path)
        width, height = image.size
        message_bits = []
        
        # Only read enough bits to determine if password protected
        for y in range(height):
            for x in range(width):
                pixel = list(image.getpixel((x, y)))
                for n in range(3):
                    message_bits.append(pixel[n] & 1)
                if len(message_bits) >= 80:  # Enough bits to check "PASSWORD:" prefix
                    break
            if len(message_bits) >= 80:
                break
        
        # Convert bits to characters
        message_bytes = [message_bits[i:i+8] for i in range(0, len(message_bits), 8)]
        prefix = ''.join([chr(int(''.join(map(str, byte)), 2)) for byte in message_bytes[:10]])
        
        os.remove(image_path)  # Clean up
        
        return {'requires_password': prefix.startswith('PASSWORD:')}
        
    except Exception as e:
        if os.path.exists(image_path):
            os.remove(image_path)
        return {'error': str(e)}, 500

@app.route('/decode', methods=['GET', 'POST'])
def decode():
    if 'username' not in session:
        flash('You need to be logged in to decode messages!', 'warning')
        return redirect(url_for('login'))
        
    if request.method == "POST":
        if 'check_only' in request.form:
            # This is handled by check_password_protection endpoint
            return '', 204
            
        img = request.files['image']
        password = request.form.get('password')
        
        if img is None or img.filename == '':
            flash('No selected file!','danger')
            return redirect(url_for('decode'))
        
        try:
            filename = secure_filename(img.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)  
            img.save(image_path)

            result_msg, error = decoded_image(image_path, password)
            
            if error:
                flash(error, 'danger')
                return redirect(url_for('decode'))

            image_path = url_for('static', filename='uploads/' + filename)
            return render_template('decode_message.html', message=result_msg, image_path=image_path)
        
        except Exception as e:
            flash(f'Error occurred while decoding the image: {str(e)}. Please ensure the image is valid and try again.', 'danger')
            return redirect(url_for('decode'))
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)

    return render_template('decode.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        # Here you can add logic to handle the contact form submission
        # For example, send an email or store in database
        
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('about_us'))

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # Set up logging
    app.run(debug=True, port=8085)  # Start the Flask application with port 8080
