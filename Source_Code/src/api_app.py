from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

def get_db_connection():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'players.db')

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row 
    return conn


@app.route('/api/players', methods=['GET'])
def search_players():
    name = request.args.get('name')
    club = request.args.get('club')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT ps.*, pv.transfer_value
        FROM player_stats ps
        LEFT JOIN player_values pv ON ps.player = pv.player
        WHERE 1=1
    """
    params = []

    if name:
        query += " AND ps.player LIKE ?"
        params.append(f"%{name}%")
    if club:
        query += " AND ps.team LIKE ?"
        params.append(f"%{club}%")

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = [dict(row) for row in rows]
    
    return jsonify(result)

if __name__ == '__main__':

    app.run(debug=True, port=5000)