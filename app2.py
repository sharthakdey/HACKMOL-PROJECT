from flask import Flask , render_template, redirect , url_for, request , flash, send_file
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask import send_from_directory
import os
from werkzeug.utils import secure_filename 
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from PyPDF2 import PdfReader
from gtts import gTTS
import uuid
import requests
import time
import requests
import time
import os



app=Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "welcome"

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(100), default="user")

    def save_hash_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_hash_password(self, password):
        
        return check_password_hash(self.password_hash, password)


class CourseContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100))
    filename = db.Column(db.String(200))
    filetype = db.Column(db.String(10))  # 'video' or 'pdf'
    uploader = db.Column(db.String(100))  # can be current_user.email
    content = db.Column(db.Text)  # 💥 NEW FIELD for description
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    
    
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def role_required(role):
    """Decorator to restrict access to specific roles"""
    def decorator(func):
        @wraps(func)  # Ensure Flask registers the function correctly
        def wrap(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash("Unauthorized Access")
                return redirect(url_for("login"))
            return func(*args, **kwargs)
        return wrap
    return decorator

@app.route("/register", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")  # ✅ Add this

        if User.query.filter_by(email=email).first():
            flash("User Already Exists")
            return redirect(url_for("signup"))  # Redirect back to signup

        user_data = User(username=username, email=email, role=role)  # ✅ Pass role
        user_data.save_hash_password(password)

        db.session.add(user_data)
        db.session.commit()
        flash("User Registered Successfully")
        return redirect(url_for("login"))

    return render_template("signup.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user_data = User.query.filter_by(email=email).first()
        if user_data and user_data.check_hash_password(password):
            login_user(user_data)
            flash("User logged in successfully")

            if user_data.role == "teacher":  
                return redirect(url_for("admin_panel"))
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password")
            return redirect(url_for("login"))

    return render_template("login.html")



@app.route("/")
def index():
    return render_template("index.html")

class Contact(db.Model):
    __tablename__ = "contact"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(200))
    subject = db.Column(db.String(200))
    message = db.Column(db.String(100))

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        subject = request.form.get("subject")
        message = request.form.get("message")
        contact_data = Contact(name=name, email=email, subject=subject, message=message)
        db.session.add(contact_data)
        db.session.commit()
        flash("Thank you for your message! We will get back to you soon.")
        return redirect(url_for("index"))
    return render_template("contact.html")


@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/courses")
def courses():
    return render_template("courses.html")



# @app.route("/single_course")
# def single_course():
#     subject = request.args.get('subject', 'Math')  # default subject
#     videos = CourseContent.query.filter_by(subject=subject, filetype='video').all()
#     pdfs = CourseContent.query.filter_by(subject=subject, filetype='pdf').all()
    
#     paired_content = list(zip(videos, pdfs))  # pairs video with pdf in order
#     return render_template("single_course.html", subject=subject, paired_content=paired_content)

@app.route("/single_course")
def single_course():
    subject = request.args.get('course', 'Math')
    search_query = request.args.get('search', '').strip().lower()

    if subject.lower() == 'mathematics':
        subject = 'Math'

    videos = CourseContent.query.filter_by(subject=subject, filetype='video').all()
    pdfs = CourseContent.query.filter_by(subject=subject, filetype='pdf').all()

    if search_query:
        videos = [v for v in videos if search_query in (v.content or '').lower()]

    paired_content = list(zip(videos, pdfs))
    return render_template("single_course.html", subject=subject, paired_content=paired_content)
@app.route("/team")
def team():
    return render_template("team.html")


@app.route("/video/<filename>")
def view_video(filename):
    return render_template("view_video.html", filename=filename)


UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        subject = request.form.get('subject')
        content = request.form.get('content')
        video = request.files.get('video')
        pdf = request.files.get('pdf')

        uploader_email = current_user.email  # ✅ Get current user's email once
        
        if video:
            filename = secure_filename(video.filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            video.save(video_path)

            # Transcribe the uploaded video and save the JSON
            # transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}.json")
            # transcribe_audio(video_path, transcript_path)

            course_video = CourseContent(
                subject=subject,
                filename=filename,
                filetype='video',
                content=content,
                uploader=uploader_email
            )
            db.session.add(course_video)

        if pdf:
            filename = secure_filename(pdf.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf.save(pdf_path)

            course_pdf = CourseContent(
                subject=subject,
                filename=filename,
                filetype='pdf',
                content=content,
                uploader=uploader_email
            )
            db.session.add(course_pdf)

        db.session.commit()
        flash("Files uploaded successfully.")
        return redirect(url_for("courses"))

    return render_template("upload.html")

@app.route('/play/<filename>')
@login_required
def play_video(filename):
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    transcript_path = video_path + '.json'

    transcript = []
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r') as f:
            data = json.load(f)
            transcript = data.get('words', [])  # list of dicts with 'text', 'start', 'end'
    else:
        flash("Captions not available yet.")

    return render_template('play_video.html', video_filename=filename, transcript=transcript)





@app.route("/base")
def base():
    return render_template("base.html")

@app.route('/lib/animate/<path:filename>')
def serve_animate(filename):
    return send_from_directory('lib/animate', filename)

@app.route('/lib/easing/<path:filename>')
def serve_easing(filename):
    return send_from_directory('lib/easing', filename)

@app.route('/lib/owlcarousel/<path:filename>')
def serve_owlcarousel(filename):
    return send_from_directory('lib/owlcarousel', filename)

@app.route('/lib/owlcarousel/assets/<path:filename>')
def serve_owlcarousel_assets(filename):
    return send_from_directory('lib/owlcarousel/assets', filename)

@app.route('/lib/waypoints/<path:filename>')
def serve_waypoints(filename):
    return send_from_directory('lib/waypoints', filename)

@app.route('/lib/wow/<path:filename>')
def serve_wow(filename):
    return send_from_directory('lib/wow', filename)



@app.route("/forgot")
def forgot():
    return render_template("forgot.html")

@app.route("/teacher")
@login_required
@role_required("admin")
def teacher():
    uploads = CourseContent.query.filter_by(uploader=current_user.email).all()
    return render_template("teacher.html", uploads=uploads)

@app.route("/delete_content/<int:content_id>", methods=["POST"])
@login_required
@role_required("teacher")
def delete_content(content_id):
    content = CourseContent.query.get_or_404(content_id)
    # Ensure the current user owns the content
    if content.uploader != current_user.email:
        flash("Unauthorized action!", "danger")
        return redirect(url_for("teacher"))
    # Optional: Delete the actual file from storage if needed
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], content.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    # Delete from database
    db.session.delete(content)
    db.session.commit()
    flash("Content deleted successfully!", "success")
    return redirect(url_for("teacher"))


@app.route("/student")
def student_timer():
    return render_template("student.html")



class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(150))
    video_id = db.Column(db.Integer)
    pdf_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
@app.route('/bookmark', methods=['POST'])
def bookmark_content():
    video_id = request.form.get('video_id')
    pdf_id = request.form.get('pdf_id')
    user = current_user.username  # or however you're tracking users

    # save bookmark to DB (you must have a bookmarks table)
    bookmark = Bookmark(video_id=video_id, pdf_id=pdf_id, user=user)
    db.session.add(bookmark)
    db.session.commit()

    flash('Content bookmarked!')
    return redirect(request.referrer)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="teacher@gmail.com").first():
        teacher = User(username="teacher", email="teacher@gmail.com", role="admin")
        teacher.save_hash_password('teacher')
        db.session.add(teacher)
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
    
    


