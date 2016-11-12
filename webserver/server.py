#!/usr/bin/env python2.7

import os
import bcrypt
import config
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
  posts = []
  suggested_users = []

  if current_user:
    recent_posts_q = """SELECT content
                        FROM Posted
                        WHERE uid IN
                          (SELECT subject_id
                           FROM Followed
                           WHERE follower_id = 
                            (SELECT uid
                             FROM Account
                             WHERE username = %s)
                           )
                        ORDER BY time_created DESC LIMIT 10"""

    suggested_users_q = """SELECT username
                           FROM Account
                           WHERE uid IN
                            (SELECT uid
                             FROM Posted
                             ORDER BY time_created DESC
                            )
                           LIMIT 10"""

    cursor = g.conn.execute(recent_posts_q, (current_user,))
    posts = [result[0] for result in cursor]

    cursor = g.conn.execute(suggested_users_q)
    suggested_users = [result[0] for result in cursor]

  else:
    recent_posts_q = """SELECT content FROM Posted
                        ORDER BY time_created DESC LIMIT 10"""
    cursor = g.conn.execute(recent_posts_q)
    posts = [result[0] for result in cursor]

  cursor.close()

  context = dict(posts=posts,
                 current_user=current_user,
                 suggested_users=suggested_users)

  return render_template("index.html", **context)

@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'GET':
    return render_template("login.html")

  username = request.form['username']

  q = "SELECT password FROM Account WHERE username = %s"
  cursor = g.conn.execute(q, (username,))
  results = [result[0] for result in cursor]
  cursor.close()

  # If username doesn't exist
  if len(results) == 0:
    return render_template("login.html", error=True)

  pw_in_db = results[0]
  hashed_pw = bcrypt.hashpw(request.form['password'], bcrypt.gensalt())

  if not bcrypt.checkpw(hashed_pw, pw_in_db):
    return render_template("login.html", error=True)

  session['username'] = username
  return redirect('/')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
  if request.method == 'GET':
    return render_template("signup.html")

  username = request.form['username']
  email = request.form['email']
  password = request.form['password']

  if not username or not email or not password:
    error_text = "Complete all fields before submitting"
    return render_template("signup.html", error_text=error_text)

  if len(password) < 6:
    error_text = "Your password must be at least 6 characters long"
    return render_template("signup.html", error_text=error_text)

  # check username is unique
  username_q = "SELECT Count(*) FROM Account WHERE username = %s"
  cursor = g.conn.execute(username_q, (username,))
  username_count = [result[0] for result in cursor]
  username_count = username_count[0]

  if username_count:
    error_text = "That username is taken"
    return render_template("signup.html", error_text=error_text)    

  # figure out what uid new user should have
  bad_q = "SELECT Max(uid) FROM Account"
  cursor = g.conn.execute(bad_q)
  uids = [result[0] for result in cursor]
  max_uid = uids[0]

  password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

  insert_q = """INSERT INTO
                Account (uid, time_created, username, email, password)
                VALUES (%s, current_timestamp, %s, %s, %s)"""
  g.conn.execute(insert_q,
    (max_uid + 1, username, email, password_hash)
  )

  session['username'] = username
  return redirect('/')

@app.route('/<username>', methods=['GET'])
def view_profile(username):
  posts, uids, followers, channels = [], [], [], []

  uid_q = """SELECT uid FROM Account WHERE username = %s"""
  cursor = g.conn.execute(uid_q, (username,))

  for result in cursor:
    uids.append(result[0])

  if len(uids) != 1:
    abort(500)

  uid = uids[0] # lol

  posts_q = """SELECT * FROM Posted
               WHERE Posted.uid = %s
               ORDER BY Posted.time_created DESC
               LIMIT 20"""

  cursor = g.conn.execute(posts_q, (uid,))

  for result in cursor:
    posts.append(result[-1])
  cursor.close()

  return render_template("user.html", posts=posts)

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
