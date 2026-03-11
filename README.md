# 💥 VOID - Ideas Voting App

## Design
- 🖤 Noir/blanc avec glitch & datamoshing psychédélique
- 🎨 Inspiré Nirvana, Aphex Twin, CRT vintage
- ✨ Scanlines animées, neon glow (magenta/cyan)

## Features
- 💭 Soumettre 1 idée par IP
- ⬆️⬇️ Système de voting Reddit-style
- 🗄️ PostgreSQL database (data persistent)
- 🚀 Déployable sur Render, Railway, etc.

## Fichiers

- `app.py` - Flask app avec SQLAlchemy
- `requirements.txt` - Dépendances Python
- `Procfile` - Config pour Render/Railway
- `templates/index.html` - Frontend noir/blanc psychédélique

## Deploy sur Render (5 min)

1. **GitHub:**
```bash
git init
git add -A
git commit -m "Initial VOID"
git remote add origin https://github.com/USERNAME/VOID.git
git push -u origin main
```

2. **Render:**
- https://render.com
- New Web Service → Connecte GitHub
- Name: `void-ideas`
- Start Command: `gunicorn app:app`
- Add PostgreSQL
- Deploy!

3. **Accès:**
```
https://void-ideas.onrender.com
```

## Local Dev

```bash
pip install -r requirements.txt
export DATABASE_URL="postgresql://localhost/void_ideas"
python app.py
```

Visite: http://localhost:5000

## API Endpoints

- `GET /` - Page index
- `POST /api/submit` - Soumettre une idée
- `GET /api/check-ip` - Vérifier si IP a soumis
- `GET /api/ideas` - Récupérer toutes les idées
- `POST /api/vote` - Voter pour une idée

## Database

Tables:
- `ideas` - Les idées
- `ip_submissions` - IPs ayant soumis (1 par IP)
- `votes` - Les votes (1 vote par IP par idée)

---

🖤 Screaming into the void since 2024
