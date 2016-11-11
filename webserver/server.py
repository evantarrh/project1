#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
import config
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session

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

@app.route('/')
def index():
  current_user = None

  if 'username' in session:
    current_user = session['username']

  cursor = g.conn.execute("SELECT username FROM Account")
  names = []
  for result in cursor:
    names.append(result[0])  # can also be accessed using result[0]
  cursor.close()

  context = dict(data=names, current_user=current_user)

  return render_template("index.html", **context)

# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  print name
  cmd = 'INSERT INTO test(name) VALUES (:name1), (:name2)'
  g.conn.execute(text(cmd), name1 = name, name2 = name)
  return redirect('/')


@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'GET':
    return render_template("login.html")

  username = request.form['username']

  q = "SELECT password FROM Account WHERE username = '{}'".format(username)
  cursor = g.conn.execute(q)
  results = []

  for result in cursor:
    results.append(result[0])  # can also be accessed using result[0]
  cursor.close()

  # If username or password is incorrect
  if (len(results) == 0 or request.form['pw'] != results[0]):
    return render_template("login.html", error=True)

  session['username'] = username
  return redirect('/')

@app.route('/<username>', methods=['GET'])
def view_profile(username):
  posts, uids, followers, channels = [], [], [], []

  uid_q = """SELECT uid FROM Account WHERE username = %s"""
  cursor = g.conn.execute(uid_q, (username))

  for result in cursor:
    uids.append(result[0])

  if len(uids) != 1:
    abort(500)

  uid = uids[0] # lol

  posts_q = """SELECT * FROM Posted
               WHERE Posted.uid = %s
               ORDER BY Posted.time_created DESC
               LIMIT 20"""

  cursor = g.conn.execute(posts_q, (uid))

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
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.secret_key = config.SESSION_KEY
    app.run(host=HOST, port=PORT, debug=True, threaded=threaded)


  run()
