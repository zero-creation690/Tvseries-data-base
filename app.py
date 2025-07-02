import sqlite3
from flask import Flask, request, jsonify, render_template_string, Response
from flask_cors import CORS
from functools import wraps
import base64

app = Flask(__name__)
CORS(app)

DB_NAME = 'movies.db'
ADMIN_USER = 'Venera'
ADMIN_PASS = 'Venera'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            season_number INTEGER NOT NULL,
            episode_number INTEGER NOT NULL,
            video_link_720p TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def check_auth(auth):
    if not auth:
        return False
    try:
        auth_type, creds = auth.split(None, 1)
        if auth_type.lower() != 'basic':
            return False
        decoded = base64.b64decode(creds).decode('utf-8')
        username, password = decoded.split(':', 1)
        return username == ADMIN_USER and password == ADMIN_PASS
    except Exception:
        return False

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', None)
        if not check_auth(auth):
            return Response(
                'Login required', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    return "📺 TV Series API running! Visit /admin to manage episodes."

# ➕ Add TV series episode
@app.route('/movies', methods=['POST'])
@requires_auth
def add_tvseries():
    data = request.json
    title = data.get('title')
    season_number = data.get('season_number')
    episode_number = data.get('episode_number')
    video_link_720p = data.get('video_link_720p')

    if not all([title, season_number, episode_number, video_link_720p]):
        return jsonify({'error': 'All fields are required'}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO movies (title, season_number, episode_number, video_link_720p)
        VALUES (?, ?, ?, ?)
    ''', (title, season_number, episode_number, video_link_720p))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({'message': 'TV series episode added', 'id': new_id}), 201

# 📋 List all TV series episodes
@app.route('/movies', methods=['GET'])
def list_tvseries():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, season_number, episode_number, video_link_720p
        FROM movies
        ORDER BY title, season_number, episode_number
    ''')
    episodes = cursor.fetchall()
    conn.close()

    result = []
    for ep in episodes:
        result.append({
            'id': ep[0],
            'title': ep[1],
            'season_number': ep[2],
            'episode_number': ep[3],
            'video_link_720p': ep[4]
        })
    return jsonify(result)

# 🔍 Get single episode by ID
@app.route('/movies/<int:movie_id>', methods=['GET'])
def get_tvseries(movie_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, season_number, episode_number, video_link_720p
        FROM movies
        WHERE id = ?
    ''', (movie_id,))
    ep = cursor.fetchone()
    conn.close()

    if not ep:
        return jsonify({'error': 'TV episode not found'}), 404

    return jsonify({
        'id': ep[0],
        'title': ep[1],
        'season_number': ep[2],
        'episode_number': ep[3],
        'video_link_720p': ep[4]
    })

# ✏️ Update episode
@app.route('/movies/<int:movie_id>', methods=['PUT'])
@requires_auth
def update_tvseries(movie_id):
    data = request.json
    title = data.get('title')
    season_number = data.get('season_number')
    episode_number = data.get('episode_number')
    video_link_720p = data.get('video_link_720p')
    
    if not all([title, season_number, episode_number, video_link_720p]):
        return jsonify({'error': 'All fields are required'}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE movies 
        SET title = ?, season_number = ?, episode_number = ?, video_link_720p = ?
        WHERE id = ?
    ''', (title, season_number, episode_number, video_link_720p, movie_id))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Episode not found'}), 404
    
    conn.commit()
    conn.close()

    return jsonify({'message': 'Episode updated successfully'})

# ❌ Delete episode
@app.route('/movies/<int:movie_id>', methods=['DELETE'])
@requires_auth
def delete_tvseries(movie_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM movies WHERE id = ?', (movie_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Episode not found'}), 404
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Episode deleted successfully'})

# 🔍 Search TV series by title
@app.route('/movies/search', methods=['GET'])
def search_tvseries():
    title = request.args.get('title')
    if not title:
        return jsonify({'error': 'Title parameter is required'}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, season_number, episode_number, video_link_720p
        FROM movies
        WHERE title LIKE ?
        ORDER BY title, season_number, episode_number
    ''', (f'%{title}%',))
    results = cursor.fetchall()
    conn.close()

    if not results:
        return jsonify({'message': 'No matching episodes found'}), 404

    return jsonify([{
        'id': r[0],
        'title': r[1],
        'season_number': r[2],
        'episode_number': r[3],
        'video_link_720p': r[4]
    } for r in results])

# 🧑‍💻 Enhanced Admin Panel
ADMIN_PAGE_HTML = '''
<!DOCTYPE html>
<html>
<head>
  <title>TV Series Admin Panel</title>
  <style>
    * { box-sizing: border-box; }
    body { 
      font-family: Arial, sans-serif; 
      background: #1a1a1a; 
      color: #ffffff; 
      padding: 20px; 
      margin: 0;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    .header { text-align: center; margin-bottom: 30px; }
    .tabs { display: flex; margin-bottom: 20px; }
    .tab { 
      padding: 10px 20px; 
      background: #333; 
      color: white; 
      border: none; 
      cursor: pointer; 
      margin-right: 5px; 
      border-radius: 5px 5px 0 0;
    }
    .tab.active { background: #dc143c; }
    .tab-content { 
      background: #2a2a2a; 
      padding: 20px; 
      border-radius: 0 5px 5px 5px; 
      min-height: 400px;
    }
    .form-group { margin-bottom: 15px; }
    .form-group label { display: block; margin-bottom: 5px; color: #ccc; }
    input, button, select { 
      width: 100%; 
      padding: 10px; 
      margin-bottom: 10px; 
      border: 1px solid #555; 
      background: #333; 
      color: white; 
      border-radius: 3px;
    }
    button { 
      background: #dc143c; 
      color: white; 
      border: none; 
      cursor: pointer; 
      font-weight: bold;
    }
    button:hover { background: #b91c3c; }
    .btn-secondary { background: #666; }
    .btn-secondary:hover { background: #555; }
    .btn-danger { background: #dc3545; }
    .btn-danger:hover { background: #c82333; }
    .search-bar { display: flex; gap: 10px; margin-bottom: 20px; }
    .search-bar input { flex: 1; margin-bottom: 0; }
    .search-bar button { width: auto; padding: 10px 20px; margin-bottom: 0; }
    .episodes-list { margin-top: 20px; }
    .episode-item { 
      background: #333; 
      padding: 15px; 
      margin-bottom: 10px; 
      border-radius: 5px; 
      border-left: 4px solid #dc143c;
    }
    .episode-header { display: flex; justify-content: between; align-items: center; margin-bottom: 10px; }
    .episode-title { font-weight: bold; font-size: 1.2em; }
    .episode-info { color: #ccc; font-size: 0.9em; margin-bottom: 10px; }
    .episode-actions { display: flex; gap: 10px; }
    .episode-actions button { width: auto; padding: 5px 15px; margin: 0; }
    .message { 
      padding: 10px; 
      margin: 10px 0; 
      border-radius: 3px; 
      background: #4caf50; 
      color: white;
    }
    .error { background: #f44336; }
    .edit-form { 
      background: #444; 
      padding: 15px; 
      margin-top: 10px; 
      border-radius: 5px; 
      display: none;
    }
    .edit-form.active { display: block; }
    .edit-form input { margin-bottom: 10px; }
    .edit-actions { display: flex; gap: 10px; }
    .edit-actions button { width: auto; padding: 8px 15px; margin: 0; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📺 TV Series Admin Panel</h1>
    </div>
    
    <div class="tabs">
      <button class="tab active" onclick="showTab('add')">Add Episode</button>
      <button class="tab" onclick="showTab('manage')">Manage Episodes</button>
    </div>
    
    <!-- Add Episode Tab -->
    <div id="addTab" class="tab-content">
      <h2>Add New Episode</h2>
      <form id="episodeForm">
        <div class="form-group">
          <label>TV Series Title:</label>
          <input type="text" name="title" placeholder="e.g., Breaking Bad" required />
        </div>
        <div class="form-group">
          <label>Season Number:</label>
          <input type="number" name="season_number" placeholder="e.g., 1" required min="1" />
        </div>
        <div class="form-group">
          <label>Episode Number:</label>
          <input type="number" name="episode_number" placeholder="e.g., 1" required min="1" />
        </div>
        <div class="form-group">
          <label>720p Video Link:</label>
          <input type="url" name="video_link_720p" placeholder="https://example.com/video.mp4" required />
        </div>
        <button type="submit">Add Episode</button>
        <div id="addMessage"></div>
      </form>
    </div>
    
    <!-- Manage Episodes Tab -->
    <div id="manageTab" class="tab-content" style="display: none;">
      <h2>Manage Episodes</h2>
      
      <div class="search-bar">
        <input type="text" id="searchInput" placeholder="Search by TV series title..." />
        <button onclick="searchEpisodes()">Search</button>
        <button class="btn-secondary" onclick="loadAllEpisodes()">Show All</button>
      </div>
      
      <div id="episodesList" class="episodes-list">
        <!-- Episodes will be loaded here -->
      </div>
      
      <div id="manageMessage"></div>
    </div>
  </div>

  <script>
    const API_AUTH = 'Basic ' + btoa('Venera:Venera');
    
    // Tab switching
    function showTab(tabName) {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(t => t.style.display = 'none');
      
      event.target.classList.add('active');
      document.getElementById(tabName + 'Tab').style.display = 'block';
      
      if (tabName === 'manage') {
        loadAllEpisodes();
      }
    }
    
    // Add episode form
    document.getElementById('episodeForm').onsubmit = async (e) => {
      e.preventDefault();
      const msg = document.getElementById('addMessage');
      msg.innerHTML = '<div class="message">Submitting...</div>';
      
      const data = Object.fromEntries(new FormData(e.target).entries());
      data.season_number = parseInt(data.season_number);
      data.episode_number = parseInt(data.episode_number);
      
      try {
        const res = await fetch('/movies', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': API_AUTH
          },
          body: JSON.stringify(data)
        });
        const json = await res.json();
        
        if (res.ok) {
          msg.innerHTML = '<div class="message">Episode added successfully!</div>';
          e.target.reset();
        } else {
          msg.innerHTML = '<div class="message error">' + (json.error || 'Error occurred') + '</div>';
        }
      } catch (err) {
        msg.innerHTML = '<div class="message error">Network error: ' + err.message + '</div>';
      }
    };
    
    // Load all episodes
    async function loadAllEpisodes() {
      const container = document.getElementById('episodesList');
      container.innerHTML = '<div class="message">Loading episodes...</div>';
      
      try {
        const res = await fetch('/movies');
        const episodes = await res.json();
        
        if (episodes.length === 0) {
          container.innerHTML = '<div class="message">No episodes found.</div>';
          return;
        }
        
        displayEpisodes(episodes);
      } catch (err) {
        container.innerHTML = '<div class="message error">Error loading episodes: ' + err.message + '</div>';
      }
    }
    
    // Search episodes
    async function searchEpisodes() {
      const query = document.getElementById('searchInput').value.trim();
      if (!query) {
        loadAllEpisodes();
        return;
      }
      
      const container = document.getElementById('episodesList');
      container.innerHTML = '<div class="message">Searching...</div>';
      
      try {
        const res = await fetch('/movies/search?title=' + encodeURIComponent(query));
        const episodes = await res.json();
        
        if (res.ok) {
          displayEpisodes(episodes);
        } else {
          container.innerHTML = '<div class="message error">No episodes found matching "' + query + '"</div>';
        }
      } catch (err) {
        container.innerHTML = '<div class="message error">Search error: ' + err.message + '</div>';
      }
    }
    
    // Display episodes
    function displayEpisodes(episodes) {
      const container = document.getElementById('episodesList');
      
      container.innerHTML = episodes.map(ep => `
        <div class="episode-item" id="episode-${ep.id}">
          <div class="episode-header">
            <div class="episode-title">${ep.title}</div>
          </div>
          <div class="episode-info">
            Season ${ep.season_number}, Episode ${ep.episode_number}
          </div>
          <div class="episode-info">
            Link: <a href="${ep.video_link_720p}" target="_blank" style="color: #4caf50;">${ep.video_link_720p}</a>
          </div>
          <div class="episode-actions">
            <button onclick="editEpisode(${ep.id})">Edit</button>
            <button class="btn-danger" onclick="deleteEpisode(${ep.id}, '${ep.title}')">Delete</button>
          </div>
          
          <div class="edit-form" id="edit-${ep.id}">
            <h4>Edit Episode</h4>
            <input type="text" id="edit-title-${ep.id}" value="${ep.title}" placeholder="Title" />
            <input type="number" id="edit-season-${ep.id}" value="${ep.season_number}" placeholder="Season" min="1" />
            <input type="number" id="edit-episode-${ep.id}" value="${ep.episode_number}" placeholder="Episode" min="1" />
            <input type="url" id="edit-link-${ep.id}" value="${ep.video_link_720p}" placeholder="Video Link" />
            <div class="edit-actions">
              <button onclick="saveEdit(${ep.id})">Save</button>
              <button class="btn-secondary" onclick="cancelEdit(${ep.id})">Cancel</button>
            </div>
          </div>
        </div>
      `).join('');
    }
    
    // Edit episode
    function editEpisode(id) {
      document.getElementById('edit-' + id).classList.add('active');
    }
    
    function cancelEdit(id) {
      document.getElementById('edit-' + id).classList.remove('active');
    }
    
    // Save edit
    async function saveEdit(id) {
      const title = document.getElementById('edit-title-' + id).value;
      const season_number = parseInt(document.getElementById('edit-season-' + id).value);
      const episode_number = parseInt(document.getElementById('edit-episode-' + id).value);
      const video_link_720p = document.getElementById('edit-link-' + id).value;
      
      if (!title || !season_number || !episode_number || !video_link_720p) {
        alert('Please fill all fields');
        return;
      }
      
      try {
        const res = await fetch('/movies/' + id, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': API_AUTH
          },
          body: JSON.stringify({ title, season_number, episode_number, video_link_720p })
        });
        const json = await res.json();
        
        if (res.ok) {
          document.getElementById('manageMessage').innerHTML = '<div class="message">Episode updated successfully!</div>';
          loadAllEpisodes();
        } else {
          alert('Error: ' + (json.error || 'Update failed'));
        }
      } catch (err) {
        alert('Network error: ' + err.message);
      }
    }
    
    // Delete episode
    async function deleteEpisode(id, title) {
      if (!confirm('Are you sure you want to delete "' + title + '"?')) {
        return;
      }
      
      try {
        const res = await fetch('/movies/' + id, {
          method: 'DELETE',
          headers: { 'Authorization': API_AUTH }
        });
        const json = await res.json();
        
        if (res.ok) {
          document.getElementById('manageMessage').innerHTML = '<div class="message">Episode deleted successfully!</div>';
          loadAllEpisodes();
        } else {
          alert('Error: ' + (json.error || 'Delete failed'));
        }
      } catch (err) {
        alert('Network error: ' + err.message);
      }
    }
    
    // Search on Enter key
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        searchEpisodes();
      }
    });
  </script>
</body>
</html>
'''

@app.route('/admin')
@requires_auth
def admin():
    return render_template_string(ADMIN_PAGE_HTML)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
