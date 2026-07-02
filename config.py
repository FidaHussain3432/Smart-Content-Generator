import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # API Keys (Placeholders for now)
    # Free APIs will be added here later
    PLAGIARISM_API_KEY = os.getenv('PLAGIARISM_API_KEY', 'PLACEHOLDER_PLAGIARISM_API_KEY')
    PLAGIARISM_API_URL = os.getenv('PLAGIARISM_API_URL', 'PLACEHOLDER_PLAGIARISM_API_URL')
    
    AI_DETECTOR_API_KEY = os.getenv('AI_DETECTOR_API_KEY', 'PLACEHOLDER_AI_DETECTOR_API_KEY')
    AI_DETECTOR_API_URL = os.getenv('AI_DETECTOR_API_URL', 'PLACEHOLDER_AI_DETECTOR_API_URL')
    
    IMAGE_SEARCH_API_KEY = os.getenv('IMAGE_SEARCH_API_KEY', 'PLACEHOLDER_IMAGE_SEARCH_API_KEY')
    IMAGE_SEARCH_API_URL = os.getenv('IMAGE_SEARCH_API_URL', 'PLACEHOLDER_IMAGE_SEARCH_API_URL')
    
    SCHOLAR_API_KEY = os.getenv('SCHOLAR_API_KEY', 'PLACEHOLDER_SCHOLAR_API_KEY')
    
    # Research settings
    MAX_RESEARCH_DEPTH = int(os.getenv('MAX_RESEARCH_DEPTH', '5'))
    MAX_SOURCES = int(os.getenv('MAX_SOURCES', '20'))
    
    # Quality thresholds
    TARGET_PLAGIARISM = float(os.getenv('TARGET_PLAGIARISM', '5.0'))
    TARGET_AI_SCORE = float(os.getenv('TARGET_AI_SCORE', '10.0'))
    MAX_REWRITE_ATTEMPTS = int(os.getenv('MAX_REWRITE_ATTEMPTS', '10'))
    
    # File upload settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    UPLOAD_FOLDER = 'uploads'
    GENERATED_FOLDER = 'uploads/generated'
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///content_generator.db')
    
    # Celery settings (for background tasks)
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
