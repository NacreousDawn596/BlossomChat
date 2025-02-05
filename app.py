from flask import Flask, request, redirect, url_for, flash, session, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO
import sqlite3
import uuid
import logging
import time
import os
import json
import datetime

app = Flask(__name__)
app.secret_key = 'meeting_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []

UPLOAD_FOLDER = 'media'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

logging.basicConfig(level=logging.DEBUG)

def query_db(query, args=(), file="", one=False):
    try:
        with sqlite3.connect(file) as conn:
            conn.row_factory = sqlite3.Row 
            cur = conn.cursor()
            cur.execute(query, args)
            logging.debug(f"qdb Executed query: {query} with args: {args}")
            rv = cur.fetchall()
            if one:
                return rv[0] if rv else None 
            return [dict(i) for i in rv]
            
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return None


def update_db(query, file="", args=()):
    try:
        with sqlite3.connect(file) as conn:
            cur = conn.cursor()
            cur.execute(query, args)
            conn.commit()
            logging.debug(f"udb Executed update: {query} with args: {args}")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        
@socketio.on("send_message")
def handle_message(msg):
    print(f"Received message: {msg}")
    messages.append(msg)
    socketio.emit("receive_message", msg)

@app.route('/logout')
def logout():
    session.clear()  
    flash("You have been logged out.")
    return redirect(url_for('login'))        

@app.route('/', methods=['GET', 'POST'])
def login():
    if "email" in session:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form['email'].lower()
        username = request.form['username']
        logging.debug(f"Attempting to log in with email: {email}")
        user = query_db('SELECT * FROM users WHERE email = ?', [email], one=True, file='users.db')
        if user is None or user['valid'] == 0:
            flash('Invalid email or username')
            update_db('INSERT INTO users VALUES (?, ?, ?, ?)', args=[email, username, int(time.time()), 0], file='users.db')
            session_id = str(uuid.uuid4())
            session['email'] = email
            session['username'] = username
            session['valid'] = 0
            session['session_id'] = session_id
        
            logging.debug(f"User {email} logged in successfully into the waitlist.")
            
            return jsonify({'success': True, 'newPath': url_for('waitlist')})
        else:
            session_id = str(uuid.uuid4())
            session['email'] = email
            session['username'] = user['username']
            session['valid'] = user['valid']
            session['session_id'] = session_id
            logging.debug(f"User {email} logged in successfully.")
            return jsonify({'success': True, 'newPath': url_for('home')})

    return render_template('login.html')

@app.route('/waitlist')
def waitlist():
    if "email" not in session:
        return redirect(url_for('login'))
    user = query_db('SELECT * FROM users WHERE email = ?', [session['email']], one=True, file='users.db')
    if user and user['valid'] > 0:
        return redirect(url_for('home'))
    socketio.emit("admin", [session['username'], session['email']])
    return render_template('waitlist.html')

@app.route('/home')
def home():
    user = query_db('SELECT * FROM users WHERE email = ?', [session['email']], one=True, file='users.db')
    if "email" not in session or user['valid'] < 1:
        return redirect(url_for('login'))
    
    return render_template('home.html', session=session, messages=messages)

@app.route('/admin')
def admin():
    user = query_db('SELECT * FROM users WHERE email = ?', [session['email']], one=True, file='users.db')
    if "email" not in session or user['valid'] != 2:
        return redirect(url_for('login'))
    
    return render_template('admin_panel.html')

@app.route('/admin/<email>')
def admin_user(email):
    if "email" not in session or session['valid'] != 2:
        return redirect(url_for('login'))
    
    user = query_db('SELECT * FROM users WHERE email = ?', [email], one=True, file='users.db')
    if user is None:
        return redirect(url_for('admin'))
    
    else:
        update_db('UPDATE users SET valid = 1 WHERE email = ?', args=[email], file='users.db')
        e = query_db("Select * FROM users WHERE valid = 1", one=False, file="users.db")
        socketio.emit('update_members', e)
        # data[1]
        socketio.emit('accepted', email)
        
    
    return render_template('admin_panel.html', user=user)