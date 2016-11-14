#!/usr/bin/env python2.7

import os
import bcrypt
import config, queries
from datetime import datetime
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import (
  Flask, request, render_template, g,
  redirect, Response, session, abort
)

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

engine = create_engine(config.DATABASE_URI)


@app.before_request
def before_request():
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@app.route('/')
def index():
  current_user = session.get('username')
  suggested_users = []

  if current_user:
    posts = queries.get_homepage_posts_for_user(current_user)
    suggested_users = queries.get_suggested_users()

  else:
    posts = queries.get_all_recent_posts()
    
  context = dict(posts=posts,
                 suggested_users=suggested_users)

  return render_template("index.html", **context)

@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'GET':
    return render_template("login.html")

  username = request.form['username'].lower()
  pw_in_db = ""

  try:
    pw_in_db = queries.get_password_for_user(username)
  except:
    return render_template("login.html", error=True)

  # we have to encode these for bcrypt
  pw_in_db = pw_in_db.encode('utf-8')
  pw_attempt = request.form['password'].encode('utf-8')

  if not bcrypt.checkpw(pw_attempt, pw_in_db):
    return render_template("login.html", error=True)

  session['username'] = username
  return redirect('/')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
  if request.method == 'GET':
    return render_template("signup.html")

  username = request.form['username'].lower()
  email = request.form['email']
  password = request.form['password']

  if not username or not email or not password:
    error_text = "Complete all fields before submitting"
    return render_template("signup.html", error_text=error_text)

  if len(password) < 6:
    error_text = "Your password must be at least 6 characters long"
    return render_template("signup.html", error_text=error_text)

  if queries.username_exists_in_db(username):
    error_text = "That username is taken"
    return render_template("signup.html", error_text=error_text)    

  password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

  queries.insert_user(username, email, password_hash)

  session['username'] = username

  return redirect('/')

@app.route('/<username>', methods=['GET'])
def view_profile(username):
  user = None
  try:
    user = queries.find_user_from_username(username)
  except:
    abort(404)

  context = {'current_user': session.get('username'),
             'user': user,
             'posts': queries.get_recent_posts_from_uid(user['uid']),
             'following': queries.get_following_given_uid(user['uid']),
             'followers': queries.get_followers_of_uid(user['uid']),
             'channels': queries.get_memberships_of_uid(user['uid'])
            }
  return render_template("user.html", **context)

@app.route('/<username>/messages', methods=['GET'])
def view_messages(username):
  messages=None
  senders=None
  timestamp=None
  try:
    messages, senders, timestamp, counter=queries.get_messages_of_user(username)
    sentmessages, recipients, senttimestamps, sentcounter=queries.get_sent_messages(username)

  except:
    abort(404)
  
  return render_template("messages.html", user=username, messages=messages, senders=senders, 
    timestamp=timestamp, counter=counter, sentmessages=sentmessages, recipients=recipients, senttimestamps=senttimestamps, 
    sentcounter=sentcounter)

@app.route('/new_message', methods=['GET'])
def add_message():
  user=session.get('username')
  if (user is None):

  recipient=request.form('recipient').lower()
  content=request.form('content')
  try:
    queries.add_message(username, recipient, content)
  except:
    abort(404)

  return redirect('/messages')
@app.route('/logout')
def logout():
  # remove the username from the session if it's there
  session.pop('username', None)
  return redirect('/')


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)

  def run(debug, threaded, host, port):
    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.secret_key = config.SESSION_KEY
    app.run(host=HOST, port=PORT, debug=True, threaded=threaded)


  run()
