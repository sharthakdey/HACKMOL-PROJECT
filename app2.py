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
import os
from bs4 import BeautifulSoup
import json
# import fitz


app=Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "welcome"

db = SQLAlchemy(app)

API_KEY = "AIzaSyCcT4Ncr-vVVb6GZEvNlkLXnmDWSLbiS4E"

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
        email = request.form["email"]
        password = request.form["password"]

        user_data = User.query.filter_by(email=email).first()  # ✅ always define it here

        if user_data and check_password_hash(user_data.password_hash, password):
            login_user(user_data)
            # if user_data.role == "admin":
            return redirect(url_for("index"))
            # elif user_data.role == "admin":
            #     return redirect(url_for("admin_dashboard"))
            # else:
            # return redirect(url_for("index"))
        else:
            flash("Invalid email or password", "error")

    return render_template("login.html")


@app.route("/")
def index():
    return render_template("index.html")

class Contact(db.Model):
    _tablename_ = "contact"
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

    paired_content = list(zip (videos, pdfs))
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
@role_required("admin")
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
        flash("Content uploaded successfully.", "success")
        return redirect(url_for('courses'))

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

@app.route("/add_bookmark/<int:content_id>", methods=["POST"])
@login_required
def add_bookmark(content_id):
    existing = Bookmark.query.filter_by(user_id=current_user.id, content_id=content_id).first()
    if not existing:
        new_bookmark = Bookmark(user_id=current_user.id, content_id=content_id)
        db.session.add(new_bookmark)
        db.session.commit()
        flash("Bookmark added successfully!")
    else:
        flash("Already bookmarked!")
    return redirect(url_for("student_dashboard"))


@app.route('/convert_to_audio', methods=['POST'])
def convert_to_audio():
    pdf_filename = request.form.get('pdf_filename')
    if not pdf_filename:
        return "No PDF filename provided", 400

    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)

    if not os.path.exists(pdf_path):
        return "PDF not found", 404

    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        return f"Error reading PDF: {e}", 500

    if not text.strip():
        return "No readable text found in PDF", 400

    # Convert text to speech
    try:
        audio_id = str(uuid.uuid4())
        audio_path = os.path.join("static/audio", f"{audio_id}.mp3")
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)

        tts = gTTS(text)
        tts.save(audio_path)

        # ✅ Directly return audio file for playback/download
        return send_file(audio_path, as_attachment=True)

    except Exception as e:
        return f"Error generating audio: {e}", 500

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

@app.route("/teacher", methods=["GET", "POST"])
@login_required
@role_required("admin")
def teacher():
    if request.method == "POST":
        file = request.files["file"]
        content_type = request.form["content_type"]
        description = request.form["description"]

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        content = CourseContent(
            filename=filename,
            content_type=content_type,
            description=description,
            uploader=current_user,
        )
        db.session.add(content)
        db.session.commit()
        return redirect(url_for("view_course"))

    return render_template("teacher.html")

@app.route("/delete_content/<int:content_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_content(content_id):
    content = CourseContent.query.get_or_404(content_id)
    # Ensure the current user owns the content
    if content.uploader != current_user.email:
        flash("Unauthorized action!", "danger")
        return redirect(url_for("index"))
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
@login_required
@role_required("user")
def student_dashboard():
    all_content = CourseContent.query.all()
    user_bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()
    bookmarked_ids = {b.content_id for b in user_bookmarks}

    return render_template("student.html", all_content=all_content, bookmarked_ids=bookmarked_ids)


@app.route('/upload_pdf', methods=['GET', 'POST'])
def upload_pdf():
    if request.method == 'POST':
        pdf_file = request.files['pdf']
        if pdf_file:
            pdf_path = f"static/uploads/{pdf_file.filename}"
            pdf_file.save(pdf_path)

            # Extract text
            doc = fitz.open(pdf_path)
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            doc.close()

            return render_template('upload_pdf.html', content=full_text)
    return render_template('upload_pdf.html')

# class Bookmark(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     user = db.Column(db.String(150))
#     video_id = db.Column(db.Integer)
#     pdf_id = db.Column(db.Integer)
#     timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content_id = db.Column(db.Integer, db.ForeignKey('course_content.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='bookmarks')
    content = db.relationship('CourseContent', backref='bookmarked_by')

    
# @app.route('/bookmark', methods=['POST'])
# def bookmark_content():
#     video_id = request.form.get('video_id')
#     pdf_id = request.form.get('pdf_id')
#     user = current_user.username  # or however you're tracking users

#     # save bookmark to DB (you must have a bookmarks table)
#     bookmark = Bookmark(video_id=video_id, pdf_id=pdf_id, user=user)
#     db.session.add(bookmark)
#     db.session.commit()

#     flash('Content bookmarked!')
#     return redirect(request.referrer)



@app.route('/bookmark', methods=['POST'])
@login_required
def bookmark_content():
    content_id = request.form.get('content_id')

    # Check if content exists
    content = CourseContent.query.get(content_id)
    if not content:
        flash("Content not found.", "error")
        return redirect("single_course")

    # Check if already bookmarked
    existing = Bookmark.query.filter_by(user_id=current_user.id, content_id=content.id).first()
    if existing:
        flash("Already bookmarked.", "info")
        return redirect('single_course')

    # Save bookmark
    bookmark = Bookmark(user_id=current_user.id, content_id=content.id)
    db.session.add(bookmark)
    db.session.commit()

    flash('Content bookmarked!', "success")
    return redirect('single_courses')


def ask_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
    
    headers = {
        "Content-Type": "application/json",
    }

    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    result = response.json()
    
    try:
        return result['candidates'][0]['content']['parts'][0]['text']
    except KeyError:
        return f"❌ Error: {result}"

def get_all_text(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text(separator=' ', strip=True)


@app.route('/fetch_article', methods=['GET', 'POST'])
def fetch_article():
    if request.method == 'POST':
        article_url = request.form.get('url')
        if not article_url:
            return "Please provide a URL.", 400

        try:
            article_text = get_all_text(article_url)
            prompt = f"Give all the content well structured about the article:\n---\n{article_text}"
            structured_text = ask_gemini(prompt)

            return render_template("upload_pdf.html", article_content=structured_text, url=article_url)

        except Exception as e:
            return f"❌ Failed to process the article: {e}", 500

    return render_template("upload_pdf.html", article_content=None)


with app.app_context():
    db.create_all()
    # if not User.query.filter_by(email="teacher@gmail.com").first():
    #     teacher = User(username="teacher", email="teacher@gmail.com", role="teacher")
    #     teacher.save_hash_password('teacher')
    #     db.session.add(teacher)
    #     db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)