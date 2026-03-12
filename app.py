from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json
import os
import re

app = Flask(__name__)
app.secret_key = 'void-secret-2024'

DATA_FILE = 'ideas.json'

# ═══════════════════════════════════════════════════════════════════════════════
# EMBED PARSING - YouTube, SoundCloud, Bandcamp
# ═══════════════════════════════════════════════════════════════════════════════

def parse_youtube(url):
    """Extract YouTube video ID and return embed info"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return {
                'platform': 'youtube',
                'id': video_id,
                'embed_url': f'https://www.youtube.com/embed/{video_id}',
                'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'
            }
    return None

def parse_soundcloud(url):
    """Extract SoundCloud URL and return embed info"""
    if 'soundcloud.com' in url:
        clean_url = url.split('?')[0]
        return {
            'platform': 'soundcloud',
            'url': clean_url,
            'embed_url': f'https://w.soundcloud.com/player/?url={clean_url}&color=%23ffffff&auto_play=false&hide_related=true&show_comments=false&show_user=true&show_reposts=false&show_teaser=false&visual=true',
            'thumbnail': None
        }
    return None

def parse_bandcamp(url):
    """Extract Bandcamp info"""
    if 'bandcamp.com' in url:
        return {
            'platform': 'bandcamp',
            'url': url,
            'embed_url': None,
            'thumbnail': None
        }
    return None

def parse_media_url(url):
    """Parse any supported media URL"""
    if not url:
        return None
    
    url = url.strip()
    result = parse_youtube(url)
    if result:
        return result
    result = parse_soundcloud(url)
    if result:
        return result
    result = parse_bandcamp(url)
    if result:
        return result
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# DATA MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure meta_votes exists
            if 'meta_votes' not in data:
                data['meta_votes'] = {}
            return data
    return {'ideas': [], 'users': {}, 'votes': {}, 'meta_votes': {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/submit', methods=['POST'])
def submit():
    data = load_data()
    ip = get_client_ip()
    
    # Check if IP already submitted
    if ip in data['users']:
        return jsonify({'success': False, 'message': 'Tu as déjà parlé'}), 400
    
    text = request.json.get('idea', '').strip()
    pseudo = request.json.get('pseudo', '').strip() or 'Anonyme'
    age = request.json.get('age', None)
    media_url = request.json.get('media_url', '').strip()
    
    # Parse media URL if provided
    media = parse_media_url(media_url) if media_url else None
    
    # Require either text or media
    if not text and not media:
        return jsonify({'success': False, 'message': 'Message ou lien requis'}), 400
    
    # 44 characters max
    if text and len(text) > 44:
        return jsonify({'success': False, 'message': 'Message trop long (44 max)'}), 400
    
    # Validate age if provided
    if age:
        try:
            age = int(age)
            if age < 1 or age > 120:
                age = None
        except:
            age = None
    
    idea = {
        'id': len(data['ideas']) + 1,
        'text': text,
        'pseudo': pseudo,
        'age': age,
        'ip': ip,
        'media': media,
        'timestamp': datetime.now().isoformat(),
        'upvotes': 0,
        'downvotes': 0,
        'edited': False,
        'meta_up': 0,
        'meta_down': 0
    }
    
    data['ideas'].append(idea)
    data['users'][ip] = {
        'pseudo': pseudo,
        'age': age,
        'timestamp': datetime.now().isoformat(),
        'idea_id': idea['id']
    }
    save_data(data)
    
    return jsonify({
        'success': True,
        'total_ideas': len(data['ideas']),
        'idea_id': idea['id']
    })

@app.route('/api/edit', methods=['POST'])
def edit():
    """Edit own message - allowed once"""
    data = load_data()
    ip = get_client_ip()
    
    # Check if user has submitted
    if ip not in data['users']:
        return jsonify({'success': False, 'message': 'Aucun message à modifier'}), 400
    
    user_idea_id = data['users'][ip].get('idea_id')
    idea = next((i for i in data['ideas'] if i['id'] == user_idea_id), None)
    
    if not idea:
        return jsonify({'success': False, 'message': 'Message introuvable'}), 404
    
    # Check if already edited
    if idea.get('edited', False):
        return jsonify({'success': False, 'message': 'Déjà modifié une fois'}), 400
    
    new_text = request.json.get('text', '').strip()
    
    if len(new_text) > 44:
        return jsonify({'success': False, 'message': 'Message trop long (44 max)'}), 400
    
    # Update the idea
    idea['text'] = new_text
    idea['edited'] = True
    idea['edited_at'] = datetime.now().isoformat()
    
    save_data(data)
    
    return jsonify({
        'success': True,
        'message': 'Modifié'
    })

@app.route('/api/check-ip', methods=['GET'])
def check_ip():
    data = load_data()
    ip = get_client_ip()
    
    user_data = data['users'].get(ip, {})
    user_idea = None
    
    if ip in data['users']:
        idea_id = user_data.get('idea_id')
        user_idea = next((i for i in data['ideas'] if i['id'] == idea_id), None)
    
    return jsonify({
        'has_submitted': ip in data['users'],
        'total_ideas': len(data['ideas']),
        'ip': ip,
        'can_edit': user_idea and not user_idea.get('edited', False) if user_idea else False,
        'user_idea': {
            'id': user_idea['id'],
            'text': user_idea.get('text', ''),
            'edited': user_idea.get('edited', False)
        } if user_idea else None
    })

@app.route('/api/ideas', methods=['GET'])
def get_ideas():
    data = load_data()
    ip = get_client_ip()
    
    ideas = []
    for idea in data['ideas']:
        vote_key = f"{ip}_{idea['id']}"
        meta_vote_key = f"{ip}_meta_{idea['id']}"
        
        # Meta vote unlocks at 10+ upvotes (not total votes)
        can_meta = idea['upvotes'] >= 10
        
        ideas.append({
            'id': idea['id'],
            'text': idea.get('text', ''),
            'pseudo': idea.get('pseudo', 'Anonyme'),
            'age': idea.get('age'),
            'media': idea.get('media'),
            'timestamp': idea['timestamp'],
            'upvotes': idea['upvotes'],
            'downvotes': idea['downvotes'],
            'score': idea['upvotes'] - idea['downvotes'],
            'user_vote': data['votes'].get(vote_key, 0),
            'edited': idea.get('edited', False),
            'can_meta_vote': can_meta,
            'meta_up': idea.get('meta_up', 0),
            'meta_down': idea.get('meta_down', 0),
            'meta_score': idea.get('meta_up', 0) - idea.get('meta_down', 0),
            'user_meta_vote': data['meta_votes'].get(meta_vote_key, 0)
        })
    
    ideas.sort(key=lambda x: x['score'], reverse=True)
    return jsonify({'ideas': ideas, 'total': len(ideas)})

@app.route('/api/vote', methods=['POST'])
def vote():
    data = load_data()
    ip = get_client_ip()
    
    try:
        idea_id = int(request.json.get('idea_id'))
        vote_type = int(request.json.get('vote'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid data'}), 400
    
    if vote_type not in [-1, 0, 1]:
        return jsonify({'success': False, 'message': 'Invalid vote'}), 400
    
    idea = next((i for i in data['ideas'] if i['id'] == idea_id), None)
    if not idea:
        return jsonify({'success': False, 'message': 'Idea not found'}), 404
    
    vote_key = f"{ip}_{idea_id}"
    old_vote = data['votes'].get(vote_key, 0)
    
    # Remove old vote
    if old_vote == 1:
        idea['upvotes'] = max(0, idea['upvotes'] - 1)
    elif old_vote == -1:
        idea['downvotes'] = max(0, idea['downvotes'] - 1)
    
    # Apply new vote
    if vote_type == 1:
        idea['upvotes'] += 1
    elif vote_type == -1:
        idea['downvotes'] += 1
    
    # Save vote state
    if vote_type == 0:
        data['votes'].pop(vote_key, None)
    else:
        data['votes'][vote_key] = vote_type
    
    save_data(data)
    
    total_votes = idea['upvotes'] + idea['downvotes']
    
    return jsonify({
        'success': True,
        'upvotes': idea['upvotes'],
        'downvotes': idea['downvotes'],
        'score': idea['upvotes'] - idea['downvotes'],
        'user_vote': vote_type,
        'can_meta_vote': total_votes >= 3
    })

@app.route('/api/meta-vote', methods=['POST'])
def meta_vote():
    """Vote on the vote - only available when idea has 10+ upvotes"""
    data = load_data()
    ip = get_client_ip()
    
    try:
        idea_id = int(request.json.get('idea_id'))
        vote_type = int(request.json.get('vote'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid data'}), 400
    
    if vote_type not in [-1, 0, 1]:
        return jsonify({'success': False, 'message': 'Invalid vote'}), 400
    
    idea = next((i for i in data['ideas'] if i['id'] == idea_id), None)
    if not idea:
        return jsonify({'success': False, 'message': 'Idea not found'}), 404
    
    # Check if meta voting is allowed (10+ upvotes)
    if idea['upvotes'] < 10:
        return jsonify({'success': False, 'message': 'Pas assez de votes positifs'}), 400
    
    meta_vote_key = f"{ip}_meta_{idea_id}"
    old_vote = data['meta_votes'].get(meta_vote_key, 0)
    
    # Initialize meta votes if needed
    if 'meta_up' not in idea:
        idea['meta_up'] = 0
    if 'meta_down' not in idea:
        idea['meta_down'] = 0
    
    # Remove old meta vote
    if old_vote == 1:
        idea['meta_up'] = max(0, idea['meta_up'] - 1)
    elif old_vote == -1:
        idea['meta_down'] = max(0, idea['meta_down'] - 1)
    
    # Apply new meta vote
    if vote_type == 1:
        idea['meta_up'] += 1
    elif vote_type == -1:
        idea['meta_down'] += 1
    
    # Save meta vote state
    if vote_type == 0:
        data['meta_votes'].pop(meta_vote_key, None)
    else:
        data['meta_votes'][meta_vote_key] = vote_type
    
    save_data(data)
    
    return jsonify({
        'success': True,
        'meta_up': idea['meta_up'],
        'meta_down': idea['meta_down'],
        'meta_score': idea['meta_up'] - idea['meta_down'],
        'user_meta_vote': vote_type
    })

# Preview endpoint
@app.route('/api/preview-media', methods=['POST'])
def preview_media():
    url = request.json.get('url', '').strip()
    media = parse_media_url(url)
    if media:
        return jsonify({'success': True, 'media': media})
    return jsonify({'success': False, 'message': 'URL non reconnue'}), 400

# Admin route
@app.route('/api/admin/data', methods=['GET'])
def admin_data():
    data = load_data()
    return jsonify(data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
