from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Fichier de stockage des idées et IPs
DATA_FILE = 'ideas_data.json'

def load_data():
    """Charge les données existantes"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'ideas': [], 'ips': {}, 'votes': {}}

def save_data(data):
    """Sauvegarde les données"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
    data = load_data()
    client_ip = get_client_ip()
    
    # Vérifier si cette IP a déjà soumis une idée
    if client_ip in data['ips']:
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
    
    # Enregistrer l'idée
    idea = {
        'id': str(len(data['ideas']) + 1),
        'text': idea_text,
        'timestamp': datetime.now().isoformat(),
        'ip': client_ip,
        'upvotes': 0,
        'downvotes': 0
    }
    
    data['ideas'].append(idea)
    data['ips'][client_ip] = datetime.now().isoformat()
    
    save_data(data)
    
    return jsonify({
        'success': True,
        'message': 'Votre idée a été enregistrée!',
        'total_ideas': len(data['ideas']),
        'idea_id': idea['id']
    })

@app.route('/api/check-ip', methods=['GET'])
def check_ip():
    """Vérifie si l'IP a déjà soumis"""
    data = load_data()
    client_ip = get_client_ip()
    
    has_submitted = client_ip in data['ips']
    
    return jsonify({
        'has_submitted': has_submitted,
        'total_ideas': len(data['ideas'])
    })

@app.route('/api/ideas', methods=['GET'])
def get_ideas():
    """Retourne toutes les idées (sans les IPs)"""
    data = load_data()
    client_ip = get_client_ip()
    
    ideas = [{
        'id': idea['id'],
        'text': idea['text'],
        'timestamp': idea['timestamp'],
        'upvotes': idea.get('upvotes', 0),
        'downvotes': idea.get('downvotes', 0),
        'score': idea.get('upvotes', 0) - idea.get('downvotes', 0),
        'user_vote': data['votes'].get(f"{client_ip}_{idea['id']}", 0)
    } for idea in data['ideas']]
    
    # Trier par score (descendant)
    ideas.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({
        'ideas': ideas,
        'total': len(ideas)
    })

@app.route('/api/vote', methods=['POST'])
def vote():
    """Vote pour une idée (upvote: 1, downvote: -1, neutral: 0)"""
    data = load_data()
    client_ip = get_client_ip()
    
    idea_id = request.json.get('idea_id')
    vote_type = request.json.get('vote')  # 1 (upvote), -1 (downvote), 0 (neutral)
    
    if not idea_id or vote_type not in [-1, 0, 1]:
        return jsonify({
            'success': False,
            'message': 'Vote invalide'
        }), 400
    
    # Trouver l'idée
    idea = next((i for i in data['ideas'] if i['id'] == idea_id), None)
    if not idea:
        return jsonify({
            'success': False,
            'message': 'Idée non trouvée'
        }), 404
    
    vote_key = f"{client_ip}_{idea_id}"
    old_vote = data['votes'].get(vote_key, 0)
    
    # Mettre à jour les votes
    if old_vote == 1:
        idea['upvotes'] -= 1
    elif old_vote == -1:
        idea['downvotes'] -= 1
    
    if vote_type == 1:
        idea['upvotes'] += 1
    elif vote_type == -1:
        idea['downvotes'] += 1
    
    # Enregistrer le nouveau vote
    if vote_type == 0:
        data['votes'].pop(vote_key, None)
    else:
        data['votes'][vote_key] = vote_type
    
    save_data(data)
    
    return jsonify({
        'success': True,
        'upvotes': idea['upvotes'],
        'downvotes': idea['downvotes'],
        'score': idea['upvotes'] - idea['downvotes'],
        'user_vote': vote_type
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
