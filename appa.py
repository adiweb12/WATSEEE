from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from functools import wraps
import random
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24) # Keep your secret key secure!

# --- Database Configuration ---
# DIRECTLY ADDING YOUR POSTGRESQL URL FOR TESTING
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://watsee_user:ShCCMWkSoOyLyL2VdI5FLYTB8efgwFd7@dpg-d1n3gf0dl3ps73fsj04g-a/watsee'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Suppress a warning

db = SQLAlchemy(app)

# --- Configuration for File Uploads ---
UPLOAD_VIDEO_FOLDER = 'static/uploads/videos'
UPLOAD_THUMBNAIL_FOLDER = 'static/uploads/thumbnails'

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
ALLOWED_THUMBNAIL_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_VIDEO_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_THUMBNAIL_FILE_SIZE = 5 * 1024 * 1024 # 5 MB

app.config['UPLOAD_VIDEO_FOLDER'] = UPLOAD_VIDEO_FOLDER
app.config['UPLOAD_THUMBNAIL_FOLDER'] = UPLOAD_THUMBNAIL_FOLDER

# Ensure the upload folders exist on startup
if not os.path.exists(UPLOAD_VIDEO_FOLDER):
    os.makedirs(UPLOAD_VIDEO_FOLDER)
if not os.path.exists(UPLOAD_THUMBNAIL_FOLDER):
    os.makedirs(UPLOAD_THUMBNAIL_FOLDER)

# --- Database Models ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), unique=True, nullable=False) # Your custom user ID
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    member_since = db.Column(db.String(20), nullable=False) # Storing as string for simplicity
    is_admin = db.Column(db.Boolean, default=False) # <--- ADDED: Admin flag for developer access

    def __repr__(self):
        return f"User('{self.email}', '{self.first_name}', Admin: {self.is_admin})"

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Auto-incrementing primary key
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(500), nullable=False) # Path to uploaded video
    thumbnail = db.Column(db.String(500), nullable=False) # Path to uploaded thumbnail
    views = db.Column(db.Integer, default=0) # Stored as integer for sorting
    upload_date = db.Column(db.String(20), nullable=False) # Storing as string for simplicity
    channel = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(20), nullable=False)
    is_featured = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"Video('{self.title}', '{self.url}')"

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

    # Ensure developer user exists and is marked as admin
    developer_email = 'watseewatcho87@gmail.com'
    developer_user = User.query.filter_by(email=developer_email).first()
    if not developer_user:
        new_developer_user = User(
            user_id='10000001',
            email=developer_email,
            password="tvbroadcast67₹", # IMPORTANT: Use secure hashing for passwords in production
            first_name="Watcho",
            last_name="Developer",
            member_since=datetime.now().strftime("%d/%m/%Y"),
            is_admin=True # <--- Set this to True for the developer user
        )
        db.session.add(new_developer_user)
        db.session.commit()
        print(f"Developer user '{developer_email}' ensured in DB with admin privileges.")
    elif not developer_user.is_admin: # If developer user exists but is not admin, make them admin
        developer_user.is_admin = True
        db.session.commit()
        print(f"Existing user '{developer_email}' updated to admin privileges.")

    # Add dummy videos if the database is empty
    if not Video.query.first():
        print("Adding dummy videos to the database...")
        dummy_videos_data = [
            {
                "title": "Amazing Wildlife Documentary: The Serengeti",
                "description": "Explore the breathtaking landscapes and diverse wildlife of the Serengeti. From the great migration to elusive predators, witness nature's raw beauty. This is a sample description of a wildlife film.",
                "url": "https://www.learningcontainer.com/wp-content/uploads/2020/05/sample-mp4-file.mp4",
                "thumbnail": "https://via.placeholder.com/320x180?text=Serengeti",
                "views": 1200000,
                "upload_date": "2 days ago",
                "channel": "Nature Explorer",
                "duration": "1:30:25",
                "is_featured": True
            },
            {
                "title": "City Skylines: Tokyo at Night",
                "description": "An mesmerizing journey through the neon-lit streets and bustling energy of Tokyo after dark. Experience the urban beauty and vibrant culture of Japan's capital.",
                "url": "http://techslides.com/demos/sample-videos/small.mp4",
                "thumbnail": "https://via.placeholder.com/320x180?text=Tokyo+Night",
                "views": 500000,
                "upload_date": "1 week ago",
                "channel": "Urban Perspectives",
                "duration": "0:45:10",
                "is_featured": False
            },
            {
                "title": "Cooking Masterclass: Italian Pasta Secrets",
                "description": "Learn the authentic techniques for making delicious homemade pasta from a master Italian chef. A step-by-step guide to perfect pasta, from dough to dish.",
                "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                "thumbnail": "https://via.placeholder.com/320x180?text=Pasta+Secrets",
                "views": 200000,
                "upload_date": "3 days ago",
                "channel": "Culinary Delights",
                "duration": "0:25:30",
                "is_featured": False
            },
            {
                "title": "Deep Sea Exploration: Mariana Trench",
                "description": "Dive into the mysterious depths of the Mariana Trench and discover creatures never seen before. An incredible underwater adventure with stunning visuals.",
                "url": "https://file-examples.com/storage/fe2532470762145b5aa56bb/2017/04/file_example_MP4_480_1_5MG.mp4",
                "thumbnail": "https://via.placeholder.com/320x180?text=Mariana+Trench",
                "views": 800000,
                "upload_date": "4 days ago",
                "channel": "Ocean Discoveries",
                "duration": "1:05:00",
                "is_featured": False
            },
            {
                "title": "Astronomy Basics: Our Solar System",
                "description": "A comprehensive guide to the planets, stars, and celestial bodies in our amazing solar system. Perfect for beginners and space enthusiasts.",
                "url": "https://storage.googleapis.com/exoplayer-test-media-0/BigBuckBunny_320x180.mp4",
                "thumbnail": "https://via.placeholder.com/320x180?text=Solar+System",
                "views": 350000,
                "upload_date": "1 month ago",
                "channel": "Space & Beyond",
                "duration": "0:50:40",
                "is_featured": False
            },
            {
                "title": "History of Ancient Rome: Rise and Fall",
                "description": "Explore the epic journey of the Roman Empire, from its humble beginnings to its eventual decline. A fascinating look at ancient civilization.",
                "url": "https://www.learningcontainer.com/wp-content/uploads/2020/05/sample-mp4-file.mp4",
                "thumbnail": "https://via.placeholder.com/320x180?text=Ancient+Rome",
                "views": 150000,
                "upload_date": "2 weeks ago",
                "channel": "Historical Docs",
                "duration": "1:15:20",
                "is_featured": False
            },
            {
                "title": "Beginner's Guide to Digital Art",
                "description": "Unlock your creativity with this easy-to-follow guide to digital painting and illustration. Perfect for aspiring artists.",
                "url": "http://techslides.com/demos/sample-videos/small.mp4",
                "thumbnail": "https://via.placeholder.com/320x180?text=Digital+Art",
                "views": 75000,
                "upload_date": "5 days ago",
                "channel": "Art Academy",
                "duration": "0:30:00",
                "is_featured": False
            },
            {
                "title": "The Art of Coffee Brewing",
                "description": "Master the secrets to making the perfect cup of coffee at home, from bean selection to brewing techniques.",
                "url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                "thumbnail": "https://via.placeholder.com/320x180?text=Coffee+Art",
                "views": 100000,
                "upload_date": "1 day ago",
                "channel": "Brew Masters",
                "duration": "0:18:45",
                "is_featured": False
            }
        ]
        for video_data in dummy_videos_data:
            new_video = Video(**video_data)
            db.session.add(new_video)
        db.session.commit()
        print("Dummy videos added.")


# --- Helper function to check allowed file extensions for videos
def allowed_video_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

# Helper function to check allowed file extensions for thumbnails
def allowed_thumbnail_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_THUMBNAIL_EXTENSIONS

# --- Decorator for Admin (Developer) Access ---
def admin_required(f): # Renamed from developer_required
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: # Check if user is logged in at all
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login_page'))
        
        user = User.query.get(session['user_id']) # Get user by ID from session

        if not user or not user.is_admin: # Check if user exists AND is admin
            flash('You do not have permission to access this page.', 'danger')
            if request.path.startswith('/api/'):
                return jsonify({"success": False, "message": "Access denied: Admin privileges required."}), 403
            return redirect(url_for('index')) # Redirect to home if not admin
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/privacy_policy.html')
def privacy_policy():
    return render_template('privacy_policy.html')

# Explicit routes for pages requiring admin access
@app.route('/developer_dashboard.html')
@admin_required # Protected route
def developer_dashboard_page():
    return render_template('developer_dashboard.html')

@app.route('/upload_video.html') # Protected route for video upload
@admin_required 
def upload_video_page():
    return render_template('upload_video.html')


# Generic route to serve other static HTML files
@app.route('/<path:filename>')
def serve_static_pages(filename):
    # Only serve files that do NOT have their own specific routes/decorators
    if filename in ['search.html', 'favorites.html', 'profile.html', 'signup.html', 'index.html',
                 'continue.html', 'list.html', 'continue_watching.html', 'video_player.html']:
        return render_template(filename)
    return "Page not found", 404

# --- API Endpoints ---

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = data.get('password') # In production, use hashed passwords (e.g., Werkzeug's generate_password_hash)

    if not all([first_name, last_name, email, password]):
        return jsonify({"success": False, "message": "All fields are required!"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered!"}), 409

    # Generate a simple user ID (you might want a more robust solution)
    user_id = str(random.randint(10000000, 99999999))
    member_since = datetime.now().strftime("%d/%m/%Y")

    new_user = User(
        user_id=user_id,
        email=email,
        password=password, # Store hashed password here in production
        first_name=first_name,
        last_name=last_name,
        member_since=member_since,
        is_admin=False # New users are not admins by default
    )
    db.session.add(new_user)
    db.session.commit()

    print(f"New user signed up: {email}, User ID: {user_id}")
    return jsonify({"success": True, "message": "Signup successful!"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if user and user.password == password: # In a real app, use user.check_password(password) for hashed passwords
        session['user_id'] = user.id # Store user ID
        session['logged_in'] = True
        session['is_admin'] = user.is_admin # Store admin status in session
        print(f"User logged in: {email}, Admin: {user.is_admin}")
        return jsonify({"success": True, "message": "Login successful!"}), 200
    else:
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

@app.route('/api/logout')
def logout():
    session.pop('user_id', None)
    session.pop('logged_in', None)
    session.pop('is_admin', None) # Clear admin status from session
    return redirect(url_for('index'))

@app.route('/api/user_data')
def get_user_data():
    if 'logged_in' in session and session['logged_in'] and 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user_data = {
                "user_id": user.user_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "member_since": user.member_since,
                "is_admin": user.is_admin # Include admin status in API response
            }
            return jsonify({"success": True, "user": user_data}), 200
        else:
            return jsonify({"success": False, "message": "User not found"}), 404
    else:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

@app.route('/api/video_data/<int:video_id>')
def get_video_data(video_id):
    video = Video.query.get(video_id)
    if video:
        video_data = {
            "id": video.id,
            "title": video.title,
            "description": video.description,
            "url": video.url,
            "thumbnail": video.thumbnail,
            "views": f"{video.views:,} Views",
            "upload_date": video.upload_date,
            "channel": video.channel,
            "duration": video.duration,
            "is_featured": video.is_featured
        }
        return jsonify({"success": True, "video": video_data}), 200
    else:
        return jsonify({"success": False, "message": "Video not found"}), 404

# --- API Endpoints for Home Page Sections ---

@app.route('/api/movies/featured', methods=['GET'])
def get_featured_movie():
    featured_video = Video.query.filter_by(is_featured=True).first()

    if featured_video:
        video_data = {
            "id": featured_video.id,
            "title": featured_video.title,
            "description": featured_video.description,
            "url": featured_video.url,
            "thumbnail": featured_video.thumbnail,
            "views": f"{featured_video.views:,} Views",
            "upload_date": featured_video.upload_date,
            "channel": featured_video.channel,
            "duration": featured_video.duration,
            "is_featured": featured_video.is_featured
        }
        return jsonify({"success": True, "movie": video_data}), 200
    
    # Fallback: if no explicit featured, pick a random one
    all_videos = Video.query.all()
    if all_videos:
        random_video = random.choice(all_videos)
        video_data = {
            "id": random_video.id,
            "title": random_video.title,
            "description": random_video.description,
            "url": random_video.url,
            "thumbnail": random_video.thumbnail,
            "views": f"{random_video.views:,} Views",
            "upload_date": random_video.upload_date,
            "channel": random_video.channel,
            "duration": random_video.duration,
            "is_featured": True # Temporarily mark as featured for display
        }
        return jsonify({"success": True, "movie": video_data}), 200

    return jsonify({"success": False, "message": "No videos available to feature."}), 404


@app.route('/api/movies/trending', methods=['GET'])
def get_trending_movies():
    # Order by views in descending order and limit to 5
    trending_videos = Video.query.order_by(Video.views.desc()).limit(5).all()
    movies_list = []
    for video in trending_videos:
        movies_list.append({
            "id": video.id,
            "title": video.title,
            "description": video.description,
            "url": video.url,
            "thumbnail": video.thumbnail,
            "views": f"{video.views:,} Views",
            "upload_date": video.upload_date,
            "channel": video.channel,
            "duration": video.duration,
            "is_featured": video.is_featured
        })
    return jsonify({"success": True, "movies": movies_list}), 200

@app.route('/api/movies/new', methods=['GET'])
def get_new_movies():
    # Order by ID in descending order (assuming higher IDs are newer) and limit to 6
    new_movies = Video.query.order_by(Video.id.desc()).limit(6).all()
    movies_list = []
    for video in new_movies:
        movies_list.append({
            "id": video.id,
            "title": video.title,
            "description": video.description,
            "url": video.url,
            "thumbnail": video.thumbnail,
            "views": f"{video.views:,} Views",
            "upload_date": video.upload_date,
            "channel": video.channel,
            "duration": video.duration,
            "is_featured": video.is_featured
        })
    return jsonify({"success": True, "movies": movies_list}), 200

@app.route('/api/movies/popular', methods=['GET'])
def get_popular_movies():
    # Simply get all and shuffle for "popular" as a demonstration
    # In a real app, 'popular' would be based on more complex logic
    all_videos = Video.query.all()
    random.shuffle(all_videos)
    movies_list = []
    for video in all_videos[:7]: # Limit to 7 random popular
        movies_list.append({
            "id": video.id,
            "title": video.title,
            "description": video.description,
            "url": video.url,
            "thumbnail": video.thumbnail,
            "views": f"{video.views:,} Views",
            "upload_date": video.upload_date,
            "channel": video.channel,
            "duration": video.duration,
            "is_featured": video.is_featured
        })
    return jsonify({"success": True, "movies": movies_list}), 200

# --- NEW: File Upload Endpoint for Video ---
@app.route('/api/upload_video_file', methods=['POST'])
@admin_required # <--- Protected by admin_required
def upload_video_file():
    if 'video_file' not in request.files:
        return jsonify({"success": False, "message": "No video file part"}), 400

    file = request.files['video_file']

    if file.filename == '':
        return jsonify({"success": False, "message": "No selected video file"}), 400

    if not allowed_video_file(file.filename):
        return jsonify({"success": False, "message": "Video file type not allowed. Allowed: mp4, mov, avi, mkv, webm"}), 400

    try:
        filename = secure_filename(file.filename)
        unique_filename = f"video_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_VIDEO_FOLDER'], unique_filename)
        file.save(filepath)

        video_url = url_for('uploaded_video_file', filename=unique_filename, _external=True)

        return jsonify({"success": True, "message": "Video file uploaded successfully!", "video_url": video_url}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error saving video file: {str(e)}"}), 500

# Endpoint to serve uploaded video files
@app.route('/static/uploads/videos/<filename>')
def uploaded_video_file(filename):
    return send_from_directory(app.config['UPLOAD_VIDEO_FOLDER'], filename)

# --- NEW: File Upload Endpoint for Thumbnail ---
@app.route('/api/upload_thumbnail_file', methods=['POST'])
@admin_required # <--- Protected by admin_required
def upload_thumbnail_file():
    if 'thumbnail_file' not in request.files:
        return jsonify({"success": False, "message": "No thumbnail file part"}), 400

    file = request.files['thumbnail_file']

    if file.filename == '':
        return jsonify({"success": False, "message": "No selected thumbnail file"}), 400

    if not allowed_thumbnail_file(file.filename):
        return jsonify({"success": False, "message": "Thumbnail file type not allowed. Allowed: png, jpg, jpeg, gif"}), 400

    try:
        filename = secure_filename(file.filename)
        unique_filename = f"thumb_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_THUMBNAIL_FOLDER'], unique_filename)
        file.save(filepath)

        thumbnail_url = url_for('uploaded_thumbnail_file', filename=unique_filename, _external=True)

        return jsonify({"success": True, "message": "Thumbnail file uploaded successfully!", "thumbnail_url": thumbnail_url}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error saving thumbnail file: {str(e)}"}), 500

# Endpoint to serve uploaded thumbnail files
@app.route('/static/uploads/thumbnails/<filename>')
def uploaded_thumbnail_file(filename):
    return send_from_directory(app.config['UPLOAD_THUMBNAIL_FOLDER'], filename)


# --- Admin (Developer) API Endpoints ---
@app.route('/api/add_video', methods=['POST'])
@admin_required # <--- Protected by admin_required
def add_video():
    data = request.json
    title = data.get('title')
    description = data.get('description')
    url = data.get('url')
    thumbnail = data.get('thumbnail')
    views_str = data.get('views', "0 Views")
    
    # Convert views string to integer
    views = 0
    try:
        # Remove commas and " Views" before parsing
        views_clean = views_str.replace(',', '').replace(' Views', '')
        if views_clean.endswith('M'):
            views = int(float(views_clean[:-1]) * 1_000_000)
        elif views_clean.endswith('K'):
            views = int(float(views_clean[:-1]) * 1_000)
        else:
            views = int(views_clean)
    except ValueError:
        views = 0 # Default to 0 if parsing fails

    upload_date = data.get('upload_date', datetime.now().strftime("%d %B %Y"))
    channel = data.get('channel', "Watcho")
    duration = data.get('duration', "00:00:00")
    is_featured = data.get('is_featured', False)

    if not all([title, description, url, thumbnail]):
        return jsonify({"success": False, "message": "Missing required video fields (title, description, URL, thumbnail)!"}), 400

    new_video = Video(
        title=title,
        description=description,
        url=url,
        thumbnail=thumbnail,
        views=views,
        upload_date=upload_date,
        channel=channel,
        duration=duration,
        is_featured=is_featured
    )
    db.session.add(new_video)
    db.session.commit()

    print(f"Video '{title}' added with ID: {new_video.id}, Featured: {is_featured}, URL: {url}, Thumbnail: {thumbnail}")
    return jsonify({"success": True, "message": "Video added successfully!", "video_id": new_video.id}), 201

@app.route('/api/remove_video', methods=['POST'])
@admin_required # <--- Protected by admin_required
def remove_video():
    data = request.json
    video_id = data.get('video_id')

    if not video_id:
        return jsonify({"success": False, "message": "Video ID is required!"}), 400

    try:
        video_to_remove = Video.query.get(video_id)
        if video_to_remove:
            # Function to safely delete a file from a specified folder
            def delete_uploaded_file(file_url, base_url_func, upload_folder):
                # Ensure _external=True is consistent for url_for when comparing against external URLs
                # Also, handle cases where URL might not be generated by url_for (e.g., placeholder URLs)
                base_url = url_for(base_url_func, filename='PLACEHOLDER_FILENAME', _external=True).replace('PLACEHOLDER_FILENAME', '')
                
                if file_url and file_url.startswith(base_url):
                    try:
                        filename_to_delete = file_url.replace(base_url, '')
                        # Basic check to prevent deleting parent directories if filename is malformed
                        if '/' not in filename_to_delete and '\\' not in filename_to_delete:
                            filepath_to_delete = os.path.join(upload_folder, filename_to_delete)
                            if os.path.exists(filepath_to_delete):
                                os.remove(filepath_to_delete)
                                print(f"Deleted physical file: {filepath_to_delete}")
                    except Exception as e:
                        print(f"Error deleting physical file {filepath_to_delete}: {e}")

            # Delete video file if it was uploaded
            delete_uploaded_file(video_to_remove.url, 'uploaded_video_file', app.config['UPLOAD_VIDEO_FOLDER'])
            # Delete thumbnail file if it was uploaded
            delete_uploaded_file(video_to_remove.thumbnail, 'uploaded_thumbnail_file', app.config['UPLOAD_THUMBNAIL_FOLDER'])

            removed_video_title = video_to_remove.title
            db.session.delete(video_to_remove)
            db.session.commit()
            print(f"Video '{removed_video_title}' (ID: {video_id}) removed.")
            return jsonify({"success": True, "message": f"Video '{video_id}' removed successfully!"}), 200
        else:
            return jsonify({"success": False, "message": "Video not found!"}), 404
    except Exception as e:
        db.session.rollback() # Rollback in case of error
        return jsonify({"success": False, "message": f"Error removing video: {str(e)}"}), 500

@app.route('/api/clear_videos', methods=['POST'])
@admin_required # <--- Protected by admin_required
def clear_all_videos():
    initial_count = Video.query.count()

    # Function to safely delete all files from a folder that match a specific pattern
    def clear_folder_files(upload_folder, prefix=""):
        for filename in os.listdir(upload_folder):
            if filename.startswith(prefix):
                filepath = os.path.join(upload_folder, filename)
                try:
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                        print(f"Deleted physical file: {filepath}")
                except Exception as e:
                    print(f"Error deleting physical file {filepath}: {e}")

    # Clear all uploaded video files
    clear_folder_files(app.config['UPLOAD_VIDEO_FOLDER'], "video_")
    # Clear all uploaded thumbnail files
    clear_folder_files(app.config['UPLOAD_THUMBNAIL_FOLDER'], "thumb_")

    try:
        db.session.query(Video).delete()
        db.session.commit()
        print(f"Removed {initial_count} videos from the database and cleared associated physical files.")
        return jsonify({"success": True, "message": f"Successfully cleared all {initial_count} videos!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error clearing videos: {str(e)}"}), 500


@app.route('/api/list_videos')
@admin_required # <--- Protected by admin_required
def list_videos():
    videos = Video.query.order_by(Video.id).all()
    video_list = []
    for video in videos:
        video_list.append({
            "id": video.id,
            "title": video.title,
            "is_featured": video.is_featured
        })
    return jsonify({"success": True, "videos": video_list}), 200

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)
