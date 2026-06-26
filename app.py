"""
Main Flask application for Volleyball Live Scorer
"""
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

db = SQLAlchemy(app)

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Tournament(db.Model):
    __tablename__ = 'tournaments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    location = db.Column(db.String(255))
    organizer = db.Column(db.String(255))
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='upcoming')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    teams = db.relationship('Team', backref='tournament', lazy=True, cascade='all, delete-orphan')

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    coach_name = db.Column(db.String(255))
    jersey_color = db.Column(db.String(100))
    players_count = db.Column(db.Integer, default=12)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    team_a_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    team_b_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    points_to_win = db.Column(db.Integer, default=25)
    status = db.Column(db.String(50), default='scheduled')
    winner_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    team_a = db.relationship('Team', foreign_keys=[team_a_id])
    team_b = db.relationship('Team', foreign_keys=[team_b_id])
    winner_team = db.relationship('Team', foreign_keys=[winner_team_id])
    tournament = db.relationship('Tournament', backref='matches')

class Set(db.Model):
    __tablename__ = 'sets'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    set_number = db.Column(db.Integer)
    team_a_score = db.Column(db.Integer, default=0)
    team_b_score = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='ongoing')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.admin is None:
            flash('You must be logged in to access this page.', 'danger')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.before_request
def load_logged_in_admin():
    admin_id = session.get('admin_id')
    g.admin = None
    if admin_id is not None:
        g.admin = Admin.query.get(admin_id)

# Routes
@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Admin Registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password or not confirm_password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        existing_user = Admin.query.filter(
            (Admin.username == username) | (Admin.email == email)
        ).first()

        if existing_user:
            flash('Username or email already taken.', 'danger')
            return render_template('register.html')

        new_admin = Admin(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_admin)
        db.session.commit()

        session.clear()
        session['admin_id'] = new_admin.id
        session['admin_username'] = new_admin.username

        flash('Successfully registered and logged in.', 'success')
        return redirect(url_for('admin_scoring'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin Login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please fill in both username and password.', 'danger')
            return render_template('login.html')

        admin = Admin.query.filter_by(username=username).first()
        if admin is None or not admin.check_password(password):
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')

        session.clear()
        session['admin_id'] = admin.id
        session['admin_username'] = admin.username

        flash('Logged in successfully.', 'success')
        return redirect(url_for('admin_scoring'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/create-tournament', methods=['GET', 'POST'])
@login_required
def create_tournament():
    """Create a new tournament"""
    if request.method == 'POST':
        tournament_name = request.form.get('tournament_name', '').strip()
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        location = request.form.get('location', '').strip()
        organizer = request.form.get('organizer', '').strip()
        description = request.form.get('description', '').strip()

        if not tournament_name:
            flash('Tournament name is required.', 'danger')
            return render_template('create_tournament.html')

        # Convert date strings to datetime objects
        start_date = None
        end_date = None
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('create_tournament.html')

        new_tournament = Tournament(
            name=tournament_name,
            admin_id=g.admin.id,
            start_date=start_date,
            end_date=end_date,
            location=location,
            organizer=organizer,
            description=description
        )
        db.session.add(new_tournament)
        db.session.commit()
        
        flash(f'Tournament "{tournament_name}" created successfully.', 'success')
        return redirect(url_for('admin_scoring'))
    return render_template('create_tournament.html')

@app.route('/create-team', methods=['GET', 'POST'])
@login_required
def create_team():
    """Create teams"""
    tournaments = Tournament.query.filter_by(admin_id=g.admin.id).all()
    
    if request.method == 'POST':
        tournament_id = request.form.get('tournament_id', '').strip()
        team_name = request.form.get('team_name', '').strip()
        coach_name = request.form.get('coach_name', '').strip()
        jersey_color = request.form.get('jersey_color', '').strip()
        players = request.form.get('players', '12')

        if not tournament_id or not team_name:
            flash('Tournament and team name are required.', 'danger')
            return render_template('create_team.html', tournaments=tournaments)

        tournament = Tournament.query.get(tournament_id)
        if not tournament or tournament.admin_id != g.admin.id:
            flash('Invalid tournament selected.', 'danger')
            return render_template('create_team.html', tournaments=tournaments)

        new_team = Team(
            name=team_name,
            tournament_id=tournament_id,
            coach_name=coach_name,
            jersey_color=jersey_color,
            players_count=players
        )
        db.session.add(new_team)
        db.session.commit()
        
        flash(f'Team "{team_name}" created successfully.', 'success')
        return redirect(url_for('admin_scoring'))
    
    return render_template('create_team.html', tournaments=tournaments)

@app.route('/create-matches', methods=['GET', 'POST'])
@login_required
def create_matches():
    """Create matches"""
    tournaments = Tournament.query.filter_by(admin_id=g.admin.id).all()
    
    if request.method == 'POST':
        tournament_id = request.form.get('tournament_id', '').strip()
        team_a_id = request.form.get('team_a_id', '').strip()
        team_b_id = request.form.get('team_b_id', '').strip()
        points_to_win = request.form.get('points_to_win', '25')

        if not all([tournament_id, team_a_id, team_b_id]):
            flash('All match fields are required.', 'danger')
            return render_template('create_matches.html', tournaments=tournaments)

        tournament = Tournament.query.get(tournament_id)
        if not tournament or tournament.admin_id != g.admin.id:
            flash('Invalid tournament selected.', 'danger')
            return render_template('create_matches.html', tournaments=tournaments)

        new_match = Match(
            tournament_id=tournament_id,
            team_a_id=team_a_id,
            team_b_id=team_b_id,
            points_to_win=int(points_to_win)
        )
        db.session.add(new_match)
        db.session.commit()
        
        # Create first set
        first_set = Set(match_id=new_match.id, set_number=1)
        db.session.add(first_set)
        db.session.commit()
        
        flash('Match setup saved successfully.', 'success')
        return redirect(url_for('admin_scoring'))
    
    return render_template('create_matches.html', tournaments=tournaments)

@app.route('/toss', methods=['GET', 'POST'])
def toss():
    """Coin flip and side/serve selection"""
    if request.method == 'POST':
        # Handle toss logic
        pass
    return render_template('toss.html')

@app.route('/admin-scoring')
@login_required
def admin_scoring():
    """Admin scoring dashboard"""
    return render_template('admin_scoring.html')

@app.route('/viewers')
def viewers():
    """Real-time score display for viewers"""
    return render_template('viewers.html')

@app.route('/api/score-update', methods=['POST'])
def score_update():
    """API endpoint for score updates"""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    set_id = data.get('setId')
    team = data.get('team')
    points = data.get('points', 1)
    
    if not set_id:
        return jsonify({'error': 'Set ID required'}), 400
    
    set_record = Set.query.get(set_id)
    if not set_record:
        return jsonify({'error': 'Set not found'}), 404
    
    if team == 'teamA':
        set_record.team_a_score += points
    elif team == 'teamB':
        set_record.team_b_score += points
    
    db.session.commit()
    return jsonify({'status': 'success', 'set_id': set_id})

@app.route('/api/score-updates', methods=['GET'])
def get_score_updates():
    """API endpoint for viewers to get current score updates for all matches"""
    matches = Match.query.options(
        db.joinedload(Match.team_a),
        db.joinedload(Match.team_b),
        db.joinedload(Match.tournament)
    ).all()
    
    updates = {}
    for match in matches:
        sets = Set.query.filter_by(match_id=match.id).order_by(Set.set_number).all()
        updates[match.id] = {
            'team_a_name': match.team_a.name if match.team_a else 'Team A',
            'team_b_name': match.team_b.name if match.team_b else 'Team B',
            'teamAScore': sets[-1].team_a_score if sets else 0,
            'teamBScore': sets[-1].team_b_score if sets else 0,
            'current_set': len(sets),
            'status': match.status,
            'tournament_name': match.tournament.name if match.tournament else '',
            'winner_team_id': match.winner_team_id
        }
    
    return jsonify({'updates': updates})

@app.route('/api/tournaments', methods=['GET'])
@login_required
def get_tournaments():
    """Get all tournaments for the logged-in admin"""
    tournaments = Tournament.query.filter_by(admin_id=g.admin.id).all()
    return jsonify([{'id': t.id, 'name': t.name} for t in tournaments])

@app.route('/api/tournament/<int:tournament_id>/matches', methods=['GET'])
@login_required
def get_tournament_matches(tournament_id):
    """Get matches for a tournament (admin only)"""
    tournament = Tournament.query.get(tournament_id)
    if not tournament or tournament.admin_id != g.admin.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    matches = Match.query.options(
        db.joinedload(Match.team_a),
        db.joinedload(Match.team_b)
    ).filter_by(tournament_id=tournament_id).all()
    
    return jsonify([{
        'id': m.id,
        'team_a_name': m.team_a.name if m.team_a else 'Team A',
        'team_b_name': m.team_b.name if m.team_b else 'Team B'
    } for m in matches])

@app.route('/api/tournament/<int:tournament_id>/teams', methods=['GET'])
@login_required
def get_tournament_teams(tournament_id):
    """Get teams for a tournament (admin only)"""
    tournament = Tournament.query.get(tournament_id)
    if not tournament or tournament.admin_id != g.admin.id:
        return jsonify({'error': 'Unauthorized'}), 403
    teams = Team.query.filter_by(tournament_id=tournament_id).all()
    return jsonify([{'id': t.id, 'name': t.name} for t in teams])

@app.route('/api/current-live-match', methods=['GET'])
def get_current_live_match():
    """Get the currently live match (one with an ongoing set)"""
    live_set = Set.query.filter_by(status='ongoing').order_by(Set.created_at.desc()).first()
    if not live_set:
        return jsonify({'match': None})
    match = Match.query.get(live_set.match_id)
    if not match:
        return jsonify({'match': None})
    return jsonify({
        'match': {
            'id': match.id,
            'team_a_name': match.team_a.name if match.team_a else 'Team A',
            'team_b_name': match.team_b.name if match.team_b else 'Team B',
            'tournament_name': match.tournament.name if match.tournament else ''
        }
    })

@app.route('/api/public/tournaments', methods=['GET'])
def get_public_tournaments():
    """Public endpoint to get all tournaments for viewers"""
    tournaments = Tournament.query.all()
    return jsonify([{'id': t.id, 'name': t.name} for t in tournaments])

@app.route('/api/public/tournament/<int:tournament_id>/matches', methods=['GET'])
def get_public_tournament_matches(tournament_id):
    """Public endpoint to get matches for a tournament"""
    matches = Match.query.options(
        db.joinedload(Match.team_a),
        db.joinedload(Match.team_b)
    ).filter_by(tournament_id=tournament_id).all()
    
    return jsonify([{
        'id': m.id,
        'team_a_id': m.team_a_id,
        'team_b_id': m.team_b_id,
        'team_a_name': m.team_a.name if m.team_a else 'Team A',
        'team_b_name': m.team_b.name if m.team_b else 'Team B',
        'points_to_win': m.points_to_win,
        'status': m.status
    } for m in matches])

@app.route('/api/undo-point', methods=['POST'])
@login_required
def undo_point():
    """API endpoint to undo last point"""
    data = request.json
    set_id = data.get('setId')
    
    set_record = Set.query.get(set_id)
    if not set_record:
        return jsonify({'error': 'Set not found'}), 404
    
    match = Match.query.get(set_record.match_id)
    if not match or match.tournament.admin_id != g.admin.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if set_record.team_a_score > 0 or set_record.team_b_score > 0:
        if set_record.team_a_score > set_record.team_b_score:
            set_record.team_a_score = max(0, set_record.team_a_score - 1)
        else:
            set_record.team_b_score = max(0, set_record.team_b_score - 1)
        db.session.commit()
    
    return jsonify({
        'status': 'success', 
        'scores': {'teamA': set_record.team_a_score, 'teamB': set_record.team_b_score}
    })

@app.route('/api/end-set', methods=['POST'])
@login_required
def end_set():
    """API endpoint to end current set"""
    data = request.json
    set_id = data.get('setId')
    
    set_record = Set.query.get(set_id)
    if not set_record:
        return jsonify({'error': 'Set not found'}), 404
    
    match = Match.query.get(set_record.match_id)
    if not match or match.tournament.admin_id != g.admin.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    set_record.status = 'completed'
    
    next_set = Set.query.filter_by(match_id=match.id).count() + 1
    new_set = Set(match_id=match.id, set_number=next_set)
    db.session.add(new_set)
    db.session.commit()
    
    return jsonify({'status': 'success', 'set': {'id': new_set.id, 'set_number': new_set.set_number}})

@app.route('/api/match/<int:match_id>', methods=['GET'])
@login_required
def get_match_details(match_id):
    """Get detailed match information"""
    match = Match.query.options(
        db.joinedload(Match.team_a),
        db.joinedload(Match.team_b)
    ).get(match_id)
    if not match:
        return jsonify({'error': 'Match not found'}), 404
    
    tournament = Tournament.query.get(match.tournament_id)
    if not tournament or tournament.admin_id != g.admin.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    sets = Set.query.filter_by(match_id=match_id).all()
    
    return jsonify({
        'id': match.id,
        'tournament_id': match.tournament_id,
        'tournament_name': tournament.name,
        'team_a_id': match.team_a_id,
        'team_a_name': match.team_a.name if match.team_a else 'Team A',
        'team_b_id': match.team_b_id,
        'team_b_name': match.team_b.name if match.team_b else 'Team B',
        'points_to_win': match.points_to_win,
        'status': match.status,
        'sets': [{
            'id': s.id,
            'set_number': s.set_number,
            'team_a_score': s.team_a_score,
            'team_b_score': s.team_b_score,
            'status': s.status
        } for s in sets]
    })

@app.route('/api/create-set', methods=['POST'])
@login_required
def create_set():
    """Create a new set for a match"""
    data = request.json
    match_id = data.get('matchId')
    
    match = Match.query.get(match_id)
    if not match or match.tournament.admin_id != g.admin.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    next_set_num = Set.query.filter_by(match_id=match_id).count() + 1
    new_set = Set(match_id=match_id, set_number=next_set_num)
    db.session.add(new_set)
    db.session.commit()
    
    return jsonify({'set': {'id': new_set.id, 'set_number': new_set.set_number}})

@app.route('/api/set-match-winner', methods=['POST'])
@login_required
def set_match_winner():
    """Set the winning team for a match"""
    data = request.json
    match_id = data.get('matchId')
    winner = data.get('winner')
    
    match = Match.query.get(match_id)
    if not match or match.tournament.admin_id != g.admin.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    match.status = 'completed'
    if winner == 'teamA':
        match.winner_team_id = match.team_a_id
    elif winner == 'teamB':
        match.winner_team_id = match.team_b_id
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'winner_team_id': match.winner_team_id
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, use_reloader=False)
