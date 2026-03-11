from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# Configuration PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost:5432/void_ideas')

# Gérer les URL postgres:// vs postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')

db = SQLAlchemy(app)

# ============ MODELS ============

class Idea(db.Model):
    __tablename__ = 'ideas'
    
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    ip = db.Column(db.String(50), nullable=False)
    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    votes = db.relationship('Vote', backref='idea', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, client_ip=None):
        user_vote = 0
        if client_ip:
            vote = Vote.query.filter_by(idea_id=self.id, ip=client_ip).first()
            if vote:
                user_vote = vote.vote_type
        
        return {
            'id': self.id,
            'text': self.text,
            'timestamp': self.created_at.isoformat(),
            'upvotes': self.upvotes,
            'downvotes': self.downvotes,
            'score': self.upvotes - self.downvotes,
            'user_vote': user_vote
        }

class IpSubmission(db.Model):
    __tablename__ = 'ip_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class Vote(db.Model):
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    idea_id = db.Column(db.Integer, db.ForeignKey('ideas.id'), nullable=False)
    ip = db.Column(db.String(50), nullable=False)
    vote_type = db.Column(db.Integer, nullable=False)  # 1 (upvote), -1 (downvote)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('idea_id', 'ip', name='unique_vote'),)

# ============ ROUTES ============

def get_client_ip():
    """Récupère l'IP du client"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/submit', methods=['POST'])
def submit_idea():
    """Soumet une nouvelle idée"""
    client_ip = get_client_ip()
    
    # Vérifier si cette IP a déjà soumis une idée
    existing = IpSubmission.query.filter_by(ip=client_ip).first()
    if existing:
        return jsonify({
            'success': False,
            'message': 'Vous avez déjà soumis une idée. Une seule idée par adresse IP.'
        }), 400
    
    idea_text = request.json.get('idea', '').strip()
    
    if not idea_text:
        return jsonify({
            'success': False,
            'message': 'L\'idée ne peut pas être vide.'
        }), 400
    
    if len(idea_text) > 500:
        return jsonify({
            'success': False,
            'message': 'L\'idée ne doit pas dépasser 500 caractères.'
        }), 400
    
    try:
        # Créer l'idée
        new_idea = Idea(text=idea_text, ip=client_ip)
        db.session.add(new_idea)
        
        # Enregistrer l'IP
        ip_submission = IpSubmission(ip=client_ip)
        db.session.add(ip_submission)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Votre idée a été enregistrée!',
            'total_ideas': Idea.query.count(),
            'idea_id': new_idea.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/check-ip', methods=['GET'])
def check_ip():
    """Vérifie si l'IP a déjà soumis"""
    client_ip = get_client_ip()
    
    has_submitted = IpSubmission.query.filter_by(ip=client_ip).first() is not None
    
    return jsonify({
        'has_submitted': has_submitted,
        'total_ideas': Idea.query.count()
    })

@app.route('/api/ideas', methods=['GET'])
def get_ideas():
    """Retourne toutes les idées (sans les IPs)"""
    client_ip = get_client_ip()
    
    ideas = Idea.query.all()
    ideas_data = [idea.to_dict(client_ip) for idea in ideas]
    
    # Trier par score (descendant)
    ideas_data.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({
        'ideas': ideas_data,
        'total': len(ideas_data)
    })

@app.route('/api/vote', methods=['POST'])
def vote():
    """Vote pour une idée (upvote: 1, downvote: -1, neutral: 0)"""
    client_ip = get_client_ip()
    
    idea_id = request.json.get('idea_id')
    vote_type = request.json.get('vote')  # 1 (upvote), -1 (downvote), 0 (neutral)
    
    if not idea_id or vote_type not in [-1, 0, 1]:
        return jsonify({
            'success': False,
            'message': 'Vote invalide'
        }), 400
    
    try:
        # Trouver l'idée
        idea = Idea.query.get(idea_id)
        if not idea:
            return jsonify({
                'success': False,
                'message': 'Idée non trouvée'
            }), 404
        
        # Vérifier s'il y a déjà un vote
        existing_vote = Vote.query.filter_by(idea_id=idea_id, ip=client_ip).first()
        
        if existing_vote:
            # Annuler l'ancien vote
            if existing_vote.vote_type == 1:
                idea.upvotes -= 1
            elif existing_vote.vote_type == -1:
                idea.downvotes -= 1
            
            if vote_type == 0:
                # Supprimer le vote
                db.session.delete(existing_vote)
            else:
                # Modifier le vote
                existing_vote.vote_type = vote_type
                if vote_type == 1:
                    idea.upvotes += 1
                elif vote_type == -1:
                    idea.downvotes += 1
        else:
            # Nouveau vote
            if vote_type != 0:
                new_vote = Vote(idea_id=idea_id, ip=client_ip, vote_type=vote_type)
                db.session.add(new_vote)
                
                if vote_type == 1:
                    idea.upvotes += 1
                elif vote_type == -1:
                    idea.downvotes += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'upvotes': idea.upvotes,
            'downvotes': idea.downvotes,
            'score': idea.upvotes - idea.downvotes,
            'user_vote': vote_type
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

# ============ INIT DATABASE ============

def init_db():
    """Initialise la base de données"""
    with app.app_context():
        db.create_all()
        print("✓ Database initialized")

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
