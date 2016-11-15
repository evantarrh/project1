#!/usr/bin/env python2.7

import bcrypt
import os
import re
import config, queries
from datetime import datetime
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import (
  abort, Flask, request, render_template, g,
  jsonify, redirect, Response, session, url_for
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
  notification_count = 0

  if current_user:
    posts = queries.get_homepage_posts_for_user(current_user)
    suggested_users = queries.get_suggested_users()
    notification_count = queries.num_notifications_for_user(current_user)

  else:
    posts = queries.get_all_recent_posts()
  
  for post in posts:
    post['replytouser']=queries.get_user_from_post(post['replyto'])

  context = dict(posts=posts,
                 suggested_users=suggested_users,
                 notification_count=notification_count)

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

  if len(username) < 3 or not re.match('^[a-z0-9]+$', username):
    error_text = """Your username must be at least 3 characters long
                and should only contain lowercase letters and numbers"""
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

  current_user = session.get('username')

  context = {
    'current_user': current_user,
    'is_following': queries.is_following(current_user, user['uid']),
    'user': user,
    'likes': queries.get_num_likes_for_uid(user['uid']),
    'posts': queries.get_recent_posts_from_uid(user['uid']),
    'following': queries.get_following_given_uid(user['uid']),
    'followers': queries.get_followers_of_uid(user['uid']),
    'channels': queries.get_memberships_of_uid(user['uid'])
  }
  for post in context['posts']:
    post['replytouser']=queries.get_user_from_post(post['replyto'])

  return render_template("user.html", **context)

@app.route('/channel/<channel_name>')
def view_channel(channel_name):  
  try:
    members = queries.get_memberships_for_channel(channel_name)
    admin = queries.get_channel_admin(channel_name)

    members.remove(admin)

    context = {
      'channel_name': channel_name,
      'admin': admin,
      'members': members,
      'is_member': queries.is_member(session.get('username'), channel_name),
      'description': queries.get_description(channel_name),
      'posts': queries.get_posts_for_channel(channel_name)
    }
  except Exception as e:
    print e
    abort(404)

  return render_template("channel.html", **context)


@app.route('/<username>/likes', methods=['GET'])
def view_likes(username):
  user = None
  try:
    user = queries.find_user_from_username(username)
  except:
    abort(404)

  context = {
    'current_user': session.get('username'),
    'user': user,
    'posts': queries.get_liked_posts(user['uid'])
  }

  return render_template("likes.html", **context)

@app.route('/notifications', methods=['GET'])
def notifications():
  current_user = session.get('username')

  if not current_user:
    abort(404)

  notifications = queries.get_notifications_for_user(current_user)

  for n in notifications:
    queries.clear_notification(n['nid'])

  context = {
    'notifications': notifications
  }

  return render_template('notifications.html', **context)


@app.route('/api/like', methods=['POST'])
def like():
  pid = request.form['pid']
  username = request.form['user']

  if not username:
    return jsonify({'liked': False})

  queries.like_post(username, pid)
  queries.like_notification(username, pid)

  return 'goood'

@app.route('/api/unlike', methods=['POST'])
def unlike():
  pid = request.form['pid']
  username = request.form['user']

  if not username:
    return jsonify({'liked': True})

  queries.unlike(username, pid)

  return 'ok'

@app.route('/api/like_query', methods=['POST'])
def like_query():
  pid = request.form['pid']
  username = request.form['user']

  if not username:
    return jsonify({'liked': False})

  data = {'liked' : queries.does_user_like_post(username, pid)}
  return jsonify(data)
  
@app.route('/api/follow', methods=['POST'])
def follow():
  follower = request.form['follower']
  followee = request.form['followee']

  if not follower or not followee:
    return jsonify({'worked': False})

  queries.follow(follower, followee)
  queries.follow_notification(follower, followee)

  return 'good'

@app.route('/api/join', methods=['POST'])
def join():
  member = request.form['member']
  channel = request.form['channel']

  if not member or not channel:
    return jsonify({'worked': False})

  queries.join_channel(member, channel)

  return 'good'
  

@app.route('/messages', methods=['GET'])
def view_messages():
  username = session.get('username')

  if not username:
    return render_template("messages.html")

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

@app.route('/new_message', methods=['GET', 'POST'])
def add_message():
  username=session.get('username')
  if request.method == 'GET':
    return render_template("newmessage.html", username=username)
  
  recipient=request.form['recipient'].lower()
  content=request.form['content']
  try:
    value=queries.add_message(username, recipient, content)
    if value is None:
      return render_template("newmessage.html", username=None)
  
  except Exception as e:
    abort(404)

  queries.message_notification(username, recipient)
  
  return redirect('/messages')

@app.route('/post/<pid>', methods=['GET', 'POST'])
def post(pid):
  posts=queries.get_post(pid)
  replyto=posts['replyto']
  replytouser=None
  username=str((queries.find_username_from_user(posts['uid']))[0])
  if replyto is not None:
    replytouser=queries.get_user_from_post(replyto)

  likes=queries.get_likes_count_for_post(pid)
  likers=queries.get_likes_for_post(pid)
  for i in range(0, len(likers)):
    likers[i]=str(likers[i][0])
  return render_template("posts.html", replytouser=replytouser, likers=likers, pid=posts['pid'], likes=likes, username=username, content=posts['content'], time=posts['date'], replyto=replyto)
  
@app.route('/new', methods=['GET', 'POST'])
def add_post():
  username=session.get('username')
  if request.method == 'GET':
    return render_template("newpost.html", username=username)
  
  if username is None:
    return render_template("newpost.html", username=None, pid=None, reply=False)
  username=session.get('username')
  content=request.form['content']
  pid=queries.add_post(None, username, content)
  pid=int((str(pid))[1] + (str(pid))[2])
  return redirect(url_for('post', pid=pid)) 

@app.route('/reply/<pid>', methods=['GET', 'POST'])
def handle_replies(pid):
  current_user=session.get('username')
  if request.method == 'GET':
    return render_template("newpost.html", username=current_user, pid=pid, reply=True)
  
  if current_user is None:
    return render_template("newpost.html", username=None, pid=None, reply=False)

  content=request.form['content']
  new_pid=queries.add_post(pid, current_user, content)
  final_pid=int((str(new_pid))[1] + (str(new_pid))[2])
  return redirect(url_for('post', pid=final_pid)) 


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
