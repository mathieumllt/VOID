from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = 'void-secret-2024'

DATA_FILE = 'ideas.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'ideas': [], 'ips': {}, 'votes': {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/submit', methods=['POST'])
def submit():
    data = load_data()
    ip = get_client_ip()
    
    if ip in data['ips']:
        return jsonify({'success': False, 'message': 'Vous avez déjà soumis'}), 400
    
    text = request.json.get('idea', '').strip()
    if not text or len(text) > 500:
        return jsonify({'success': False, 'message': 'Idée invalide'}), 400
    
    idea = {
        'id': len(data['ideas']) + 1,
        'text': text,
        'timestamp': datetime.now().isoformat(),
        'upvotes': 0,
        'downvotes': 0
    }
    
    data['ideas'].append(idea)
    data['ips'][ip] = datetime.now().isoformat()
    save_data(data)
    
    return jsonify({
        'success': True,
        'total_ideas': len(data['ideas']),
        'idea_id': idea['id']
    })

@app.route('/api/check-ip', methods=['GET'])
def check_ip():
    data = load_data()
    ip = get_client_ip()
    return jsonify({
        'has_submitted': ip in data['ips'],
        'total_ideas': len(data['ideas'])
    })

@app.route('/api/ideas', methods=['GET'])
def get_ideas():
    data = load_data()
    ip = get_client_ip()
    
    ideas = []
    for idea in data['ideas']:
        vote_key = f"{ip}_{idea['id']}"
        ideas.append({
            'id': idea['id'],
            'text': idea['text'],
            'timestamp': idea['timestamp'],
            'upvotes': idea['upvotes'],
            'downvotes': idea['downvotes'],
            'score': idea['upvotes'] - idea['downvotes'],
            'user_vote': data['votes'].get(vote_key, 0)
        })
    
    ideas.sort(key=lambda x: x['score'], reverse=True)
    return jsonify({'ideas': ideas, 'total': len(ideas)})

@app.route('/api/vote', methods=['POST'])
def vote():
    data = load_data()
    ip = get_client_ip()
    
    idea_id = request.json.get('idea_id')
    vote_type = request.json.get('vote')
    
    if vote_type not in [-1, 0, 1]:
        return jsonify({'success': False}), 400
    
    idea = next((i for i in data['ideas'] if i['id'] == idea_id), None)
    if not idea:
        return jsonify({'success': False}), 404
    
    vote_key = f"{ip}_{idea_id}"
    old_vote = data['votes'].get(vote_key, 0)
    
    if old_vote == 1:
        idea['upvotes'] -= 1
    elif old_vote == -1:
        idea['downvotes'] -= 1
    
    if vote_type == 1:
        idea['upvotes'] += 1
    elif vote_type == -1:
        idea['downvotes'] += 1
    
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
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
