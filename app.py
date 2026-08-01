# ============================================================
# YASH WORLD - Premium Survey Application
# Flask Version - Production Ready for Render
# Enhanced with Proper Cascade Deletion
# ============================================================

import os
import json
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from sqlalchemy import func, desc

# ============================================================
# LOGGING CONFIGURATION
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'yash-world-secret-key-2024')

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///survey.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload configuration
UPLOAD_FOLDER = 'media'
ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEOS = {'mp4', 'webm', 'mov', 'avi', 'mkv'}
ALLOWED_AUDIO = {'mp3', 'wav', 'ogg', 'm4a', 'mp4', 'aac', 'flac'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# ============================================================
# CREATE FOLDERS
# ============================================================
def create_folders():
    folders = [
        'media',
        'media/images',
        'media/videos',
        'media/audio',
        'media/background_music',
        'media/questions/images',
        'media/questions/videos',
        'media/questions/audio',
        'media/options/images',
        'media/options/videos',
        'media/answers/images',
        'media/answers/videos',
        'media/answers/audio',
        'media/feedback/images',
        'media/feedback/videos',
        'media/feedback/audio',
        'media/final_feedback/images',
        'media/final_feedback/videos',
        'media/final_feedback/audio',
        'media/typing_texts',
        'static',
        'static/css',
        'static/js',
        'templates',
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)

create_folders()

# ============================================================
# DATABASE MODELS
# ============================================================

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class TypingText(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BackgroundMusic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    duration = db.Column(db.Integer, default=0)
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    text = db.Column(db.Text, nullable=False)
    marks = db.Column(db.Integer, default=1)
    order = db.Column(db.Integer, default=0)
    
    image = db.Column(db.String(500))
    video = db.Column(db.String(500))
    audio = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships with cascade delete
    options = db.relationship('QuestionOption', backref='question', cascade='all, delete-orphan', lazy=True)
    two_marks_answer = db.relationship('TwoMarksAnswer', backref='question', cascade='all, delete-orphan', uselist=False)
    responses = db.relationship('UserResponse', backref='question', cascade='all, delete-orphan', lazy=True)

class QuestionOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    
    image = db.Column(db.String(500))
    video = db.Column(db.String(500))

class TwoMarksAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False, unique=True)
    answer_text = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    
    image = db.Column(db.String(500))
    video = db.Column(db.String(500))
    audio = db.Column(db.String(500))

class UserResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)
    text_response = db.Column(db.Text)
    marks_earned = db.Column(db.Float, default=0)
    is_revealed = db.Column(db.Boolean, default=False)
    time_spent = db.Column(db.Integer, default=0)
    
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='responses')

user_response_options = db.Table('user_response_options',
    db.Column('user_response_id', db.Integer, db.ForeignKey('user_response.id', ondelete='CASCADE')),
    db.Column('question_option_id', db.Integer, db.ForeignKey('question_option.id', ondelete='CASCADE'))
)

class FinalFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, unique=True)
    rating = db.Column(db.String(20))
    liked = db.Column(db.Text)
    improvements = db.Column(db.Text)
    recommend = db.Column(db.String(20))
    additional = db.Column(db.Text)
    
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='final_feedback')

class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_title = db.Column(db.String(200), default='YASH WORLD')
    site_tagline = db.Column(db.String(200), default='Premium Survey Application')
    welcome_message = db.Column(db.Text)
    enable_music = db.Column(db.Boolean, default=True)
    enable_typing = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================================
# FILE UPLOAD HELPERS
# ============================================================

def get_file_extension(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def is_allowed_image(filename):
    return get_file_extension(filename) in ALLOWED_IMAGES

def is_allowed_video(filename):
    return get_file_extension(filename) in ALLOWED_VIDEOS

def is_allowed_audio(filename):
    return get_file_extension(filename) in ALLOWED_AUDIO

def save_file(file, subfolder, allowed_extensions):
    if not file or file.filename == '':
        return None
    
    extension = get_file_extension(file.filename)
    if extension not in allowed_extensions:
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    secure_name = secure_filename(file.filename)
    filename = f"{timestamp}_{secure_name}"
    
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(folder_path, exist_ok=True)
    
    file_path = os.path.join(folder_path, filename)
    file.save(file_path)
    
    return os.path.join(subfolder, filename).replace('\\', '/')

def save_image(file, subfolder='images'):
    return save_file(file, subfolder, ALLOWED_IMAGES)

def save_video(file, subfolder='videos'):
    return save_file(file, subfolder, ALLOWED_VIDEOS)

def save_audio(file, subfolder='audio'):
    return save_file(file, subfolder, ALLOWED_AUDIO)

def delete_media_file(file_path):
    """Delete a media file from the server"""
    if file_path:
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], file_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                return True
            except Exception as e:
                logger.error(f"Error deleting file {full_path}: {e}")
                return False
    return False

# ============================================================
# LOGIN MANAGER
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin access for this page.', 'danger')
            return redirect(url_for('survey'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# CONTEXT PROCESSOR
# ============================================================

@app.context_processor
def utility_processor():
    def get_site_settings():
        settings = SiteSettings.query.first()
        if not settings:
            settings = SiteSettings()
            db.session.add(settings)
            db.session.commit()
        return settings
    return dict(get_site_settings=get_site_settings)

# ============================================================
# ROUTES - AUTHENTICATION
# ============================================================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('survey'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('survey'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ============================================================
# ROUTES - USER SURVEY
# ============================================================

@app.route('/survey')
@login_required
def survey():
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings()
        db.session.add(settings)
        db.session.commit()
    
    has_typing_text = TypingText.query.filter_by(is_active=True).first() is not None
    has_questions = Question.query.count() > 0
    has_music = BackgroundMusic.query.filter_by(is_active=True).first() is not None
    
    typing_text = TypingText.query.filter_by(is_active=True).order_by(TypingText.created_at.desc()).first()
    
    questions = Question.query.order_by(Question.order).all()
    responses = UserResponse.query.filter_by(user_id=current_user.id).all()
    responded_ids = [r.question_id for r in responses]
    
    seen_typing = session.get('seen_typing', False)
    show_typing = has_typing_text and not seen_typing and settings.enable_typing
    
    if not has_typing_text and not has_questions and not has_music:
        return render_template('survey.html', 
            is_completely_empty=True,
            has_typing_text=False,
            has_questions=False,
            has_music=False,
            typing_text='',
            questions=[],
            current_index=0,
            total=0,
            responses=responses,
            progress=0,
            show_typing_page=False,
            seen_typing=True,
            settings=settings
        )
    
    current_index = request.args.get('index', 0, type=int)
    total_questions = len(questions)
    
    if total_questions == 0:
        return render_template('survey.html', 
            is_completely_empty=False,
            has_typing_text=bool(typing_text),
            has_questions=False,
            has_music=has_music,
            typing_text=typing_text.text if typing_text else '',
            questions=[],
            current_index=0,
            total=0,
            responses=responses,
            progress=0,
            show_typing_page=show_typing,
            seen_typing=seen_typing,
            settings=settings
        )
    
    if show_typing:
        return render_template('survey.html',
            is_completely_empty=False,
            has_typing_text=True,
            has_questions=True,
            has_music=has_music,
            question=None,
            questions=questions,
            current_index=0,
            total=total_questions,
            responded_ids=responded_ids,
            user_response=None,
            two_marks_answer=None,
            music_tracks=BackgroundMusic.query.filter_by(is_active=True).order_by(BackgroundMusic.order).all(),
            progress=0,
            selected_options=[],
            typing_text=typing_text.text if typing_text else '',
            show_typing_page=True,
            seen_typing=seen_typing,
            settings=settings
        )
    
    if current_index >= total_questions:
        if len(responses) >= total_questions:
            return redirect(url_for('final_feedback'))
        else:
            for i, q in enumerate(questions):
                if q.id not in responded_ids:
                    current_index = i
                    break
    
    question = questions[current_index] if current_index < total_questions else None
    two_marks_answer = None
    if question and question.type == 'two_marks':
        two_marks_answer = TwoMarksAnswer.query.filter_by(question_id=question.id).first()
    
    user_response = None
    if question:
        user_response = UserResponse.query.filter_by(
            user_id=current_user.id, 
            question_id=question.id
        ).first()
    
    music_tracks = BackgroundMusic.query.filter_by(is_active=True).order_by(BackgroundMusic.order).all()
    
    selected_options = []
    if user_response:
        selected_options = db.session.query(QuestionOption.id).join(
            user_response_options, 
            QuestionOption.id == user_response_options.c.question_option_id
        ).filter(
            user_response_options.c.user_response_id == user_response.id
        ).all()
        selected_options = [opt[0] for opt in selected_options]
    
    progress = ((current_index + 1) / total_questions * 100) if total_questions > 0 else 0
    
    return render_template('survey.html',
        is_completely_empty=False,
        has_typing_text=bool(typing_text),
        has_questions=True,
        has_music=has_music,
        question=question,
        questions=questions,
        current_index=current_index,
        total=total_questions,
        responded_ids=responded_ids,
        user_response=user_response,
        two_marks_answer=two_marks_answer,
        music_tracks=music_tracks,
        progress=progress,
        selected_options=selected_options,
        typing_text=typing_text.text if typing_text else '',
        show_typing_page=False,
        seen_typing=True,
        settings=settings
    )

@app.route('/seen_typing', methods=['POST'])
@login_required
def seen_typing():
    session['seen_typing'] = True
    return jsonify({'success': True})

@app.route('/save_response', methods=['POST'])
@login_required
def save_response():
    data = request.get_json()
    
    question_id = data.get('question_id')
    selected_options = data.get('selected_options', [])
    text_response = data.get('text_response', '')
    question_type = data.get('question_type', '')
    is_revealed = data.get('is_revealed', False)
    time_spent = data.get('time_spent', 0)
    
    question = Question.query.get(question_id)
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    
    marks_earned = 0
    if question_type == 'survey':
        marks_earned = 1 if selected_options else 0
    elif question_type == 'quiz':
        correct_options = QuestionOption.query.filter_by(question_id=question_id, is_correct=True).all()
        correct_ids = [opt.id for opt in correct_options]
        if selected_options:
            if all(opt_id in correct_ids for opt_id in selected_options) and len(selected_options) == len(correct_ids):
                marks_earned = 1
    elif question_type == 'two_marks':
        marks_earned = 2 if is_revealed else 0
    
    user_response = UserResponse.query.filter_by(
        user_id=current_user.id,
        question_id=question_id
    ).first()
    
    if user_response:
        user_response.marks_earned = marks_earned
        user_response.is_revealed = is_revealed
        user_response.text_response = text_response
        user_response.time_spent = time_spent
        
        db.session.execute(
            user_response_options.delete().where(
                user_response_options.c.user_response_id == user_response.id
            )
        )
        
        if selected_options:
            for opt_id in selected_options:
                db.session.execute(
                    user_response_options.insert().values(
                        user_response_id=user_response.id,
                        question_option_id=opt_id
                    )
                )
    else:
        user_response = UserResponse(
            user_id=current_user.id,
            question_id=question_id,
            marks_earned=marks_earned,
            is_revealed=is_revealed,
            text_response=text_response,
            time_spent=time_spent
        )
        db.session.add(user_response)
        db.session.flush()
        
        if selected_options:
            for opt_id in selected_options:
                db.session.execute(
                    user_response_options.insert().values(
                        user_response_id=user_response.id,
                        question_option_id=opt_id
                    )
                )
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'marks_earned': marks_earned,
        'is_revealed': is_revealed
    })

@app.route('/final_feedback', methods=['GET', 'POST'])
@login_required
def final_feedback():
    if request.method == 'POST':
        feedback = FinalFeedback.query.filter_by(user_id=current_user.id).first()
        if not feedback:
            feedback = FinalFeedback(user_id=current_user.id)
            db.session.add(feedback)
        
        feedback.rating = request.form.get('rating', '')
        feedback.liked = request.form.get('liked', '')
        feedback.improvements = request.form.get('improvements', '')
        feedback.recommend = request.form.get('recommend', '')
        feedback.additional = request.form.get('additional', '')
        
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('summary'))
    
    return render_template('survey.html', show_final_feedback=True)

@app.route('/summary')
@login_required
def summary():
    responses = UserResponse.query.filter_by(user_id=current_user.id).all()
    total_marks = sum(r.marks_earned for r in responses)
    
    for response in responses:
        response.options = db.session.query(QuestionOption).join(
            user_response_options,
            QuestionOption.id == user_response_options.c.question_option_id
        ).filter(
            user_response_options.c.user_response_id == response.id
        ).all()
    
    questions = Question.query.all()
    possible_marks = sum(q.marks for q in questions)
    
    final_feedback = FinalFeedback.query.filter_by(user_id=current_user.id).first()
    
    return render_template('survey.html',
        show_summary=True,
        responses=responses,
        total_marks=total_marks,
        possible_marks=possible_marks,
        final_feedback=final_feedback,
        questions=questions
    )

# ============================================================
# ADMIN ROUTES
# ============================================================

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_questions = Question.query.count()
    total_responses = UserResponse.query.count()
    total_feedback = FinalFeedback.query.count()
    
    question_types = db.session.query(
        Question.type,
        db.func.count(Question.id)
    ).group_by(Question.type).all()
    
    recent_responses = UserResponse.query.order_by(
        UserResponse.submitted_at.desc()
    ).limit(10).all()
    
    typing_text = TypingText.query.filter_by(is_active=True).order_by(TypingText.created_at.desc()).first()
    
    return render_template('admin_panel.html',
        section='dashboard',
        total_users=total_users,
        total_questions=total_questions,
        total_responses=total_responses,
        total_feedback=total_feedback,
        question_types=question_types,
        recent_responses=recent_responses,
        typing_text=typing_text.text if typing_text else ''
    )

@app.route('/admin/typing-text', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_typing_text():
    if request.method == 'POST':
        text = request.form.get('typing_text', '').strip()
        if text:
            TypingText.query.update({TypingText.is_active: False})
            new_text = TypingText(text=text, is_active=True)
            db.session.add(new_text)
            db.session.commit()
            flash('Typing text updated successfully!', 'success')
        else:
            flash('Please enter some text.', 'danger')
        return redirect(url_for('admin_typing_text'))
    
    typing_texts = TypingText.query.order_by(TypingText.created_at.desc()).all()
    active_text = TypingText.query.filter_by(is_active=True).first()
    
    return render_template('admin_panel.html', 
        section='typing_text',
        typing_texts=typing_texts,
        active_text=active_text
    )

@app.route('/admin/typing-text/<int:text_id>/activate')
@login_required
@admin_required
def admin_activate_typing_text(text_id):
    TypingText.query.update({TypingText.is_active: False})
    text = TypingText.query.get_or_404(text_id)
    text.is_active = True
    db.session.commit()
    flash('Typing text activated!', 'success')
    return redirect(url_for('admin_typing_text'))

@app.route('/admin/typing-text/<int:text_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_typing_text(text_id):
    text = TypingText.query.get_or_404(text_id)
    db.session.delete(text)
    db.session.commit()
    flash('Typing text deleted!', 'success')
    return redirect(url_for('admin_typing_text'))

@app.route('/admin/questions')
@login_required
@admin_required
def admin_questions():
    questions = Question.query.order_by(Question.order).all()
    return render_template('admin_panel.html', section='questions', questions=questions)

@app.route('/admin/questions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_question():
    if request.method == 'POST':
        question = Question()
        question.type = request.form.get('type')
        question.text = request.form.get('text')
        question.marks = int(request.form.get('marks', 1))
        question.order = int(request.form.get('order', 0))
        
        if not question.text:
            flash('Question text is required.', 'danger')
            return redirect(request.url)
        
        if 'image' in request.files:
            path = save_image(request.files['image'], 'questions/images')
            if path:
                question.image = path
        
        if 'video' in request.files:
            path = save_video(request.files['video'], 'questions/videos')
            if path:
                question.video = path
        
        if 'audio' in request.files:
            path = save_audio(request.files['audio'], 'questions/audio')
            if path:
                question.audio = path
        
        db.session.add(question)
        db.session.flush()
        
        if question.type in ['survey', 'quiz']:
            option_texts = request.form.getlist('option_text[]')
            option_images = request.files.getlist('option_image[]')
            option_videos = request.files.getlist('option_video[]')
            correct_answers = request.form.getlist('is_correct[]')
            
            for i, text in enumerate(option_texts):
                if text.strip():
                    option = QuestionOption(
                        question_id=question.id,
                        text=text.strip(),
                        is_correct=(str(i) in correct_answers),
                        order=i
                    )
                    
                    if i < len(option_images) and option_images[i] and option_images[i].filename:
                        path = save_image(option_images[i], 'options/images')
                        if path:
                            option.image = path
                    
                    if i < len(option_videos) and option_videos[i] and option_videos[i].filename:
                        path = save_video(option_videos[i], 'options/videos')
                        if path:
                            option.video = path
                    
                    db.session.add(option)
        
        elif question.type == 'two_marks':
            answer_text = request.form.get('answer_text', '')
            explanation = request.form.get('explanation', '')
            
            if answer_text:
                answer = TwoMarksAnswer(
                    question_id=question.id,
                    answer_text=answer_text,
                    explanation=explanation
                )
                
                if 'answer_image' in request.files and request.files['answer_image'].filename:
                    path = save_image(request.files['answer_image'], 'answers/images')
                    if path:
                        answer.image = path
                
                if 'answer_video' in request.files and request.files['answer_video'].filename:
                    path = save_video(request.files['answer_video'], 'answers/videos')
                    if path:
                        answer.video = path
                
                if 'answer_audio' in request.files and request.files['answer_audio'].filename:
                    path = save_audio(request.files['answer_audio'], 'answers/audio')
                    if path:
                        answer.audio = path
                
                db.session.add(answer)
        
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('admin_questions'))
    
    return render_template('admin_panel.html', section='add_question')

@app.route('/admin/questions/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    
    if request.method == 'POST':
        question.type = request.form.get('type')
        question.text = request.form.get('text')
        question.marks = int(request.form.get('marks', 1))
        question.order = int(request.form.get('order', 0))
        
        if 'image' in request.files and request.files['image'].filename:
            # Delete old image
            if question.image:
                delete_media_file(question.image)
            path = save_image(request.files['image'], 'questions/images')
            if path:
                question.image = path
        
        if 'video' in request.files and request.files['video'].filename:
            if question.video:
                delete_media_file(question.video)
            path = save_video(request.files['video'], 'questions/videos')
            if path:
                question.video = path
        
        if 'audio' in request.files and request.files['audio'].filename:
            if question.audio:
                delete_media_file(question.audio)
            path = save_audio(request.files['audio'], 'questions/audio')
            if path:
                question.audio = path
        
        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('admin_questions'))
    
    options = QuestionOption.query.filter_by(question_id=question_id).order_by(QuestionOption.order).all()
    two_marks_answer = TwoMarksAnswer.query.filter_by(question_id=question_id).first()
    
    return render_template('admin_panel.html',
        section='edit_question',
        question=question,
        options=options,
        two_marks_answer=two_marks_answer
    )

@app.route('/admin/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_question(question_id):
    try:
        question = Question.query.get_or_404(question_id)
        
        # Delete associated media files
        if question.image:
            delete_media_file(question.image)
        if question.video:
            delete_media_file(question.video)
        if question.audio:
            delete_media_file(question.audio)
        
        # Delete options and their media
        options = QuestionOption.query.filter_by(question_id=question_id).all()
        for option in options:
            if option.image:
                delete_media_file(option.image)
            if option.video:
                delete_media_file(option.video)
        
        # Delete 2 marks answer and its media
        two_marks = TwoMarksAnswer.query.filter_by(question_id=question_id).first()
        if two_marks:
            if two_marks.image:
                delete_media_file(two_marks.image)
            if two_marks.video:
                delete_media_file(two_marks.video)
            if two_marks.audio:
                delete_media_file(two_marks.audio)
        
        # Delete all responses for this question
        UserResponse.query.filter_by(question_id=question_id).delete()
        
        # Delete the question (cascade will delete options and 2 marks)
        db.session.delete(question)
        db.session.commit()
        
        flash('Question and all associated data deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting question {question_id}: {e}")
        flash('Error deleting question. Please try again.', 'danger')
    
    return redirect(url_for('admin_questions'))

@app.route('/admin/options/add', methods=['POST'])
@login_required
@admin_required
def admin_add_option():
    question_id = request.form.get('question_id', type=int)
    text = request.form.get('text')
    is_correct = request.form.get('is_correct') == 'on'
    order = int(request.form.get('order', 0))
    
    if not text:
        flash('Option text is required.', 'danger')
        return redirect(url_for('admin_edit_question', question_id=question_id))
    
    option = QuestionOption(
        question_id=question_id,
        text=text,
        is_correct=is_correct,
        order=order
    )
    
    if 'image' in request.files:
        path = save_image(request.files['image'], 'options/images')
        if path:
            option.image = path
    
    if 'video' in request.files:
        path = save_video(request.files['video'], 'options/videos')
        if path:
            option.video = path
    
    db.session.add(option)
    db.session.commit()
    flash('Option added successfully!', 'success')
    return redirect(url_for('admin_edit_question', question_id=question_id))

@app.route('/admin/options/<int:option_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_option(option_id):
    option = QuestionOption.query.get_or_404(option_id)
    question_id = option.question_id
    
    # Delete media files
    if option.image:
        delete_media_file(option.image)
    if option.video:
        delete_media_file(option.video)
    
    db.session.delete(option)
    db.session.commit()
    flash('Option deleted successfully!', 'success')
    return redirect(url_for('admin_edit_question', question_id=question_id))

@app.route('/admin/two-marks-answer/add', methods=['POST'])
@login_required
@admin_required
def admin_add_two_marks_answer():
    question_id = request.form.get('question_id', type=int)
    answer_text = request.form.get('answer_text')
    explanation = request.form.get('explanation')
    
    existing = TwoMarksAnswer.query.filter_by(question_id=question_id).first()
    if existing:
        existing.answer_text = answer_text
        existing.explanation = explanation
        answer = existing
    else:
        answer = TwoMarksAnswer(
            question_id=question_id,
            answer_text=answer_text,
            explanation=explanation
        )
        db.session.add(answer)
    
    if 'image' in request.files and request.files['image'].filename:
        if answer.image:
            delete_media_file(answer.image)
        path = save_image(request.files['image'], 'answers/images')
        if path:
            answer.image = path
    
    if 'video' in request.files and request.files['video'].filename:
        if answer.video:
            delete_media_file(answer.video)
        path = save_video(request.files['video'], 'answers/videos')
        if path:
            answer.video = path
    
    if 'audio' in request.files and request.files['audio'].filename:
        if answer.audio:
            delete_media_file(answer.audio)
        path = save_audio(request.files['audio'], 'answers/audio')
        if path:
            answer.audio = path
    
    db.session.commit()
    flash('Answer saved successfully!', 'success')
    return redirect(url_for('admin_edit_question', question_id=question_id))

@app.route('/admin/music')
@login_required
@admin_required
def admin_music():
    tracks = BackgroundMusic.query.order_by(BackgroundMusic.order).all()
    return render_template('admin_panel.html', section='music', tracks=tracks)

@app.route('/admin/music/add', methods=['POST'])
@login_required
@admin_required
def admin_add_music():
    title = request.form.get('title')
    order = int(request.form.get('order', 0))
    is_active = request.form.get('is_active') == 'on'
    
    if not title:
        flash('Track title is required.', 'danger')
        return redirect(url_for('admin_music'))
    
    if 'file' not in request.files:
        flash('No file uploaded!', 'danger')
        return redirect(url_for('admin_music'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected!', 'danger')
        return redirect(url_for('admin_music'))
    
    path = save_audio(file, 'background_music')
    if not path:
        flash('Invalid file format! Supported: mp3, wav, ogg, m4a, mp4', 'danger')
        return redirect(url_for('admin_music'))
    
    track = BackgroundMusic(
        title=title,
        filename=file.filename,
        file_path=path,
        order=order,
        is_active=is_active
    )
    
    db.session.add(track)
    db.session.commit()
    flash('Music track added successfully!', 'success')
    return redirect(url_for('admin_music'))

@app.route('/admin/music/<int:track_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_music(track_id):
    track = BackgroundMusic.query.get_or_404(track_id)
    
    # Delete the file
    if track.file_path:
        delete_media_file(track.file_path)
    
    db.session.delete(track)
    db.session.commit()
    flash('Track deleted successfully!', 'success')
    return redirect(url_for('admin_music'))

@app.route('/admin/music/<int:track_id>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_music(track_id):
    track = BackgroundMusic.query.get_or_404(track_id)
    track.is_active = not track.is_active
    db.session.commit()
    flash('Track status updated!', 'success')
    return redirect(url_for('admin_music'))

@app.route('/admin/responses')
@login_required
@admin_required
def admin_responses():
    responses = UserResponse.query.order_by(UserResponse.submitted_at.desc()).all()
    
    for response in responses:
        response.options = db.session.query(QuestionOption).join(
            user_response_options,
            QuestionOption.id == user_response_options.c.question_option_id
        ).filter(
            user_response_options.c.user_response_id == response.id
        ).all()
    
    return render_template('admin_panel.html', section='responses', responses=responses)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin_panel.html', section='users', users=users)

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings()
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        settings.site_title = request.form.get('site_title', 'YASH WORLD')
        settings.site_tagline = request.form.get('site_tagline', 'Premium Survey Application')
        settings.welcome_message = request.form.get('welcome_message', '')
        settings.enable_music = request.form.get('enable_music') == 'on'
        settings.enable_typing = request.form.get('enable_typing') == 'on'
        
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin_settings'))
    
    return render_template('admin_panel.html', section='settings', settings=settings)

@app.route('/admin/export-data')
@login_required
@admin_required
def admin_export_data():
    data = {
        'users': [{'id': u.id, 'username': u.username, 'is_admin': u.is_admin, 'created_at': u.created_at.isoformat()} for u in User.query.all()],
        'questions': [{'id': q.id, 'type': q.type, 'text': q.text, 'marks': q.marks} for q in Question.query.all()],
        'responses': [{'id': r.id, 'user_id': r.user_id, 'question_id': r.question_id, 'marks_earned': r.marks_earned} for r in UserResponse.query.all()],
        'feedback': [{'id': f.id, 'user_id': f.user_id, 'rating': f.rating, 'recommend': f.recommend} for f in FinalFeedback.query.all()]
    }
    return jsonify(data)

@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, message='Page not found'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('error.html', error_code=500, message='Internal server error'), 500

@app.errorhandler(403)
def forbidden(error):
    return render_template('error.html', error_code=403, message='Access denied'), 403

# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    with app.app_context():
        db.create_all()
        
        # Create admin user
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logger.info("✅ Admin user created: admin / admin123")
        
        # Create test user
        lory = User.query.filter_by(username='lory').first()
        if not lory:
            lory = User(username='lory', is_admin=False)
            lory.set_password('lory')
            db.session.add(lory)
            db.session.commit()
            logger.info("✅ Test user created: lory / lory")
        
        # Create default settings
        settings = SiteSettings.query.first()
        if not settings:
            settings = SiteSettings(
                site_title='YASH WORLD',
                site_tagline='Premium Survey Application',
                enable_music=True,
                enable_typing=True
            )
            db.session.add(settings)
            db.session.commit()
            logger.info("✅ Default settings created")
        
        logger.info("\n" + "="*50)
        logger.info("🚀 YASH WORLD Survey Application")
        logger.info("="*50)
        logger.info("📍 Server running at: http://localhost:5000")
        logger.info("🔑 Admin Login: admin / admin123")
        logger.info("👤 User Login: lory / lory")
        logger.info("⚠️  All content is stored permanently until deleted")
        logger.info("="*50 + "\n")

# ============================================================
# RUN THE APPLICATION
# ============================================================

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    app.run(debug=debug, host='0.0.0.0', port=port)
