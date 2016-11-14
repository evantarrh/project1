from flask import g
from datetime import datetime

###############################
#
#    POST QUERIES
#
###############################

def get_homepage_posts_for_user(username, limit=20, **kwargs):
    offset = kwargs.get('offset', 0)

    recent_posts_q = """SELECT Posted.*, Account.username
                FROM Posted, Account
                WHERE Posted.uid = Account.uid
                AND Posted.uid IN
                  (SELECT subject_id
                   FROM Followed
                   WHERE follower_id = 
                        (SELECT uid
                         FROM Account
                          WHERE username = %s)
                    )
                ORDER BY Posted.time_created DESC
                OFFSET {} LIMIT %s""".format(offset)

    cursor = g.conn.execute(recent_posts_q, (username, limit))

    posts = [{
            'pid': result[0],
            'replyto': result[1],
            'date': datetime.strftime(result[3], "%b %d"),
            'content': result[4],
            'username': result[5]
          } for result in cursor]

    for post in posts:
        post['likes'] = get_likes_count_for_post(post['pid'])

    cursor.close()

    return posts

def get_all_recent_posts(limit=20, **kwargs):
    """
    Returns the {limit} most recent posts.
    """
    offset = kwargs.get('offset', 0)

    # recent_posts_q = """SELECT t.*, Count(Liked.liker_id)
    #                     FROM (
    #                         SELECT Posted.*, Account.username
    #                         FROM Posted, Account
    #                         WHERE Posted.uid = Account.uid
    #                     ) AS t
    #                     JOIN Liked ON Liked.post_id = t.pid
    #                     ORDER BY t.time_created DESC LIMIT %s"""


    recent_posts_q = """SELECT Posted.*, Account.username
                        FROM Posted, Account
                        WHERE Posted.uid = Account.uid
                        ORDER BY Posted.time_created DESC
                        OFFSET {} LIMIT %s""".format(offset)


    cursor = g.conn.execute(recent_posts_q, (limit,))
    posts = [{
            'pid': result[0],
            'replyto': result[1],
            'date': datetime.strftime(result[3], "%b %d"),
            'content': result[4],
            'username': result[5]
          } for result in cursor]

    for post in posts:
        post['likes'] = get_likes_count_for_post(post['pid'])

    cursor.close()

    return posts

def get_recent_posts_from_uid(uid, limit=20, **kwargs):
    offset = kwargs.get('offset', 0)

    posts_q = """SELECT * FROM Posted
               WHERE uid = %s
               ORDER BY time_created DESC
               OFFSET {} LIMIT 20""".format(offset)
    user_q = """SELECT username FROM Account
                WHERE uid = %s"""


    cursor = g.conn.execute(posts_q, (uid,))
    posts = [{
            'pid': result[0],
            'replyto': result[1],
            'date': datetime.strftime(result[3], "%b %d"),
            'content': result[4]
          } for result in cursor]

    cursor = g.conn.execute(user_q, (uid,))
    username = [result[0] for result in cursor]
    for post in posts:
        post['username'] = username[0]

    for post in posts:
        post['likes'] = get_likes_count_for_post(post['pid'])

    cursor.close()

    return posts

def get_likes_count_for_post(pid):
    likes_q = """SELECT Count(*) FROM Liked
                 WHERE post_id = %s"""
    cursor = g.conn.execute(likes_q, (pid,))
    likes = [result[0] for result in cursor]
    cursor.close()

    return int(likes[0])

###############################
#
#    ACCOUNT QUERIES
#
###############################

def get_suggested_users(limit=10):
    """
    Returns the usernames of the {limit} users who have posted
    the most recently.
    """

    suggested_users_q = """SELECT username
                           FROM Account
                           WHERE uid IN
                            (SELECT uid
                             FROM Posted
                             ORDER BY time_created DESC
                            )
                           LIMIT %s"""

    cursor = g.conn.execute(suggested_users_q, (limit,))
    users = [result[0] for result in cursor]
    cursor.close()
    return users

def get_password_for_user(username):
    q = "SELECT password FROM Account WHERE username = %s"

    cursor = g.conn.execute(q, (username,))
    results = [result[0] for result in cursor]
    cursor.close()

    if len(results) == 0:
        raise RuntimeError

    return results[0]

def username_exists_in_db(username):
    username_q = "SELECT Count(*) FROM Account WHERE username = %s"
    cursor = g.conn.execute(username_q, (username,))
    username_count = [result[0] for result in cursor]
    cursor.close()

    username_count = username_count[0]

    return not username_count

def insert_user(username, email, password_hash):
    insert_q = """INSERT INTO
                Account (time_created, username, email, password)
                VALUES (current_timestamp, %s, %s, %s)"""
    g.conn.execute(insert_q, (username, email, password_hash))

def find_user_from_username(username):
    user_q = """SELECT * FROM Account WHERE username = %s"""
    cursor = g.conn.execute(user_q, (username,))
    user = [result for result in cursor]
    cursor.close()

    if len(user) != 1:
        raise RuntimeError

    user = {
        'uid': user[0][0],
        'username': user[0][2],
        'bio': user[0][4]
    }

    return user

###############################
#
#    FOLLOWING QUERIES
#
###############################

def get_following_given_uid(uid):
    following_q = """SELECT Account.username FROM Account, Followed
               WHERE Account.uid = Followed.subject_id
               AND Followed.follower_id = %s
               LIMIT 20"""
    cursor = g.conn.execute(following_q, (uid,))
    following = [result[0] for result in cursor]
    cursor.close()

    return following

def get_followers_of_uid(uid):
    follower_q = """SELECT Account.username FROM Account, Followed
           WHERE Account.uid = Followed.follower_id
           AND Followed.subject_id = %s
           LIMIT 20"""
    cursor = g.conn.execute(follower_q, (uid,))
    followers = [result[0] for result in cursor]
    cursor.close()

    return followers


###############################
#
#    CHANNEL QUERIES
#
###############################

def get_memberships_of_uid(uid):
    channel_q = """SELECT Channel.name FROM Channel, Membership
           WHERE Membership.gid = Channel.gid
           AND Membership.uid = %s
           LIMIT 20"""

    cursor = g.conn.execute(channel_q, (uid,))
    channels = [result[0] for result in cursor]
    cursor.close()

    return channels

def find_username_from_user(uid):
    user_q="""SELECT Account.username FROM Account WHERE Account.uid=%s"""
    cursor=g.conn.execute(user_q, (uid))
    return [result[0] for result in cursor]
###############################
#
#    MESSAGES QUERIES
#
###############################
def get_sent_messages(username):
    user_q="""SELECT Account.uid FROM Account
                WHERE Account.username= %s"""
    cursor = g.conn.execute(user_q, (username))
    user= [result[0] for result in cursor]
    messages_q="""SELECT sent_message.content, sent_message.recipient_id, sent_message.sent_time FROM sent_message
                    WHERE sent_message.sender_id = %s"""
    cursor = g.conn.execute(messages_q, (user))
    messages=[]
    senders=[]
    timestamps=[]
    counter=0
    for result in cursor:
        messages.append(result[0])
        senders.append(find_username_from_user(result[1]))
        timestamps.append(datetime.strftime(result[2], "%b %d"))
        counter+=1
    for i in range(0, len(senders)):
        senders[i]=str(senders[i][0])

    cursor.close()
    return messages, senders, timestamps, counter
def get_messages_of_user(username):
    user_q= """SELECT Account.uid FROM Account
                WHERE Account.username= %s"""
    cursor = g.conn.execute(user_q, (username))
    user= [result[0] for result in cursor]
    messages_q="""SELECT sent_message.content, sent_message.sender_id, sent_message.sent_time FROM sent_message
                    WHERE sent_message.recipient_id = %s"""
    cursor = g.conn.execute(messages_q, (user))
    messages=[]
    senders=[]
    timestamps=[]
    counter=0
    for result in cursor:
        messages.append(result[0])
        senders.append(find_username_from_user(result[1]))
        timestamps.append(datetime.strftime(result[2], "%b %d"))
        counter+=1
    for i in range(0, len(senders)):
        senders[i]=str(senders[i][0])

    cursor.close()
    return messages, senders, timestamps, counter
def add_message(username, recipient, content):
    sender_id=find_user_from_username(username)
    recipient_id=find_user_from_username(recipient)
    time=datetime.datetime.now().time()
    user_q="""INSERT INTO sent_message (sender_id, recipient_id, sent_time, content) 
                VALUES (%s, %s, %s, %s)"""
    cursor=g.conn.execute(user_q, (sender_id, recipient_id, str(time), content))
    cursor.close()


