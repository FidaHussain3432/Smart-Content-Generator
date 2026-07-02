from flask import Flask, render_template, request, jsonify, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from celery import Celery
from datetime import datetime
import os
import json
from config import DevelopmentConfig
from modules.research_engine import ResearchEngine
from modules.content_rewriter import ContentRewriter
from modules.plagiarism_checker import PlagiarismChecker
from modules.ai_detector import AIDetector
from modules.image_finder import ImageFinder
from modules.document_generator import DocumentGenerator
from modules.quality_controller import QualityController

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    projects = db.relationship('Project', backref='author', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(500), nullable=False)
    target_words = db.Column(db.Integer, nullable=False)
    min_words = db.Column(db.Integer)
    max_words = db.Column(db.Integer)
    status = db.Column(db.String(50), default='pending')  # pending, researching, writing, checking, completed, failed
    plagiarism_score = db.Column(db.Float, default=100.0)
    ai_score = db.Column(db.Float, default=100.0)
    iteration_count = db.Column(db.Integer, default=0)
    output_file = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Store settings as JSON
    settings = db.Column(db.Text, default='{}')
    
    def get_settings(self):
        return json.loads(self.settings)
    
    def set_settings(self, settings_dict):
        self.settings = json.dumps(settings_dict)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html', 
                         title='Smart Content Generator',
                         meta_description='AI-powered research and content generation tool',
                         structured_data=get_structured_data())

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard for creating and managing projects"""
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.created_at.desc()).all()
    return render_template('dashboard.html', 
                         title='Dashboard - Smart Content Generator',
                         projects=projects)

@app.route('/api/create_project', methods=['POST'])
@login_required
def create_project():
    """API endpoint to create new content generation project"""
    try:
        data = request.json
        
        # Validate input
        topic = data.get('topic', '').strip()
        min_words = int(data.get('min_words', 20000))
        max_words = int(data.get('max_words', 30000))
        target_words = int(data.get('target_words', 25000))
        
        # Settings
        settings = {
            'include_images': data.get('include_images', True),
            'image_per_section': data.get('image_per_section', 2),
            'citation_style': data.get('citation_style', 'APA'),
            'language': data.get('language', 'english'),
            'target_plagiarism': float(data.get('target_plagiarism', 5.0)),
            'target_ai_score': float(data.get('target_ai_score', 10.0)),
            'rewrite_attempts': int(data.get('rewrite_attempts', 10)),
            'include_references': data.get('include_references', True),
            'output_format': data.get('output_format', 'docx'),
            'research_sources': data.get('research_sources', ['web', 'scholar', 'articles']),
            'auto_images': data.get('auto_images', True),
            'grammar_check': data.get('grammar_check', True)
        }
        
        # Create project in database
        project = Project(
            user_id=current_user.id,
            topic=topic,
            target_words=target_words,
            min_words=min_words,
            max_words=max_words,
            settings=json.dumps(settings)
        )
        db.session.add(project)
        db.session.commit()
        
        # Start background task
        task = generate_content_task.delay(project.id, topic, settings)
        
        return jsonify({
            'success': True,
            'project_id': project.id,
            'task_id': task.id,
            'message': 'Project created successfully. Content generation started.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/project_status/<int:project_id>')
@login_required
def project_status(project_id):
    """Get current status of a project"""
    project = Project.query.get_or_404(project_id)
    
    if project.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'project_id': project.id,
        'status': project.status,
        'plagiarism_score': project.plagiarism_score,
        'ai_score': project.ai_score,
        'iteration_count': project.iteration_count,
        'updated_at': project.updated_at.isoformat()
    })

@app.route('/api/download/<int:project_id>')
@login_required
def download_file(project_id):
    """Download generated file"""
    project = Project.query.get_or_404(project_id)
    
    if project.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if project.status != 'completed':
        return jsonify({'error': 'File not ready yet'}), 400
    
    file_path = project.output_file
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(file_path, as_attachment=True, 
                    download_name=f"{project.topic[:50]}_generated.docx")

@app.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('settings.html', 
                         title='Settings - Smart Content Generator',
                         user=current_user)

@app.route('/editor/<int:project_id>')
@login_required
def editor(project_id):
    """Content editor page"""
    project = Project.query.get_or_404(project_id)
    
    if project.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return render_template('editor.html', 
                         title=f'Editor - {project.topic}',
                         project=project)

# Celery Tasks
@celery.task(bind=True)
def generate_content_task(self, project_id, topic, settings):
    """Main background task for content generation"""
    
    with app.app_context():
        project = Project.query.get(project_id)
        
        try:
            # Update status
            project.status = 'researching'
            db.session.commit()
            self.update_state(state='PROGRESS', meta={'status': 'Researching...'})
            
            # Step 1: Research
            research_engine = ResearchEngine(settings)
            research_data = research_engine.research_topic(topic, 
                                                          min_words=project.min_words,
                                                          max_words=project.max_words)
            
            # Step 2: Find relevant images
            if settings.get('include_images', True):
                project.status = 'finding_images'
                db.session.commit()
                
                image_finder = ImageFinder(settings)
                images = image_finder.find_images_for_content(research_data, topic)
            else:
                images = []
            
            # Step 3: Rewrite content
            project.status = 'writing'
            db.session.commit()
            self.update_state(state='PROGRESS', meta={'status': 'Generating content...'})
            
            rewriter = ContentRewriter(settings)
            content = rewriter.rewrite_content(research_data, topic, images)
            
            # Step 4: Quality control loop
            quality_controller = QualityController(settings)
            
            for iteration in range(settings.get('rewrite_attempts', 10)):
                project.status = 'checking'
                project.iteration_count = iteration + 1
                db.session.commit()
                
                self.update_state(state='PROGRESS', 
                                meta={'status': f'Quality check iteration {iteration + 1}...'})
                
                # Check plagiarism
                plagiarism_checker = PlagiarismChecker(settings)
                plagiarism_score = plagiarism_checker.check_plagiarism(content)
                
                # Check AI content
                ai_detector = AIDetector(settings)
                ai_score = ai_detector.detect_ai_content(content)
                
                # Update project scores
                project.plagiarism_score = plagiarism_score
                project.ai_score = ai_score
                db.session.commit()
                
                # Check if quality meets targets
                if quality_controller.is_quality_acceptable(plagiarism_score, ai_score):
                    project.status = 'generating_document'
                    db.session.commit()
                    break
                else:
                    # Rewrite again with feedback
                    content = rewriter.improve_content(content, 
                                                      plagiarism_feedback=plagiarism_score,
                                                      ai_feedback=ai_score)
            
            # Step 5: Generate final document
            document_generator = DocumentGenerator(settings)
            output_file = document_generator.generate_docx(content, project.topic, images)
            
            # Update project as completed
            project.status = 'completed'
            project.output_file = output_file
            db.session.commit()
            
            return {
                'status': 'completed',
                'project_id': project_id,
                'file_path': output_file,
                'plagiarism_score': plagiarism_score,
                'ai_score': ai_score
            }
            
        except Exception as e:
            project.status = 'failed'
            db.session.commit()
            raise e

# Dynamic update system
@app.route('/api/dynamic_update', methods=['POST'])
@login_required
def dynamic_update():
    """Dynamic update system for making changes without importing files"""
    try:
        data = request.json
        update_type = data.get('type')
        update_data = data.get('data')
        
        response = {
            'success': True,
            'message': 'Update processed successfully',
            'changes': {}
        }
        
        if update_type == 'rewrite_section':
            # Rewrite specific section
            section_id = update_data.get('section_id')
            new_style = update_data.get('style', 'academic')
            
            rewriter = ContentRewriter({})
            rewritten_section = rewriter.rewrite_section(section_id, new_style)
            
            response['changes']['new_content'] = rewritten_section
            
        elif update_type == 'add_images':
            # Add images to specific sections
            sections = update_data.get('sections', [])
            image_count = update_data.get('image_count', 2)
            
            image_finder = ImageFinder({})
            new_images = image_finder.find_images_for_sections(sections, image_count)
            
            response['changes']['images'] = new_images
            
        elif update_type == 'change_style':
            # Change entire document style
            project_id = update_data.get('project_id')
            new_style = update_data.get('style')
            
            # Apply new style to project
            project = Project.query.get(project_id)
            settings = project.get_settings()
            settings['style'] = new_style
            project.set_settings(settings)
            db.session.commit()
            
            response['changes']['message'] = f'Style changed to {new_style}'
            
        elif update_type == 'expand_section':
            # Expand a specific section with more content
            section_id = update_data.get('section_id')
            additional_words = update_data.get('additional_words', 500)
            
            # Logic to expand section
            expanded_content = "Expanded content placeholder..."
            
            response['changes']['expanded_content'] = expanded_content
            
        elif update_type == 'custom_prompt':
            # Apply custom user prompt to modify content
            section_id = update_data.get('section_id')
            custom_prompt = update_data.get('prompt')
            
            # Process with custom prompt
            modified_content = f"Content modified based on: {custom_prompt}"
            
            response['changes']['modified_content'] = modified_content
            
        else:
            response['success'] = False
            response['message'] = f'Unknown update type: {update_type}'
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

def get_structured_data():
    """Generate structured data for SEO"""
    structured_data = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": "Smart Content Generator",
        "description": "AI-powered research and content generation tool with automatic plagiarism checking",
        "applicationCategory": "ContentGeneration",
        "operatingSystem": "All",
        "url": "https://smartcontentgenerator.com",
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
        }
    }
    return json.dumps(structured_data)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
