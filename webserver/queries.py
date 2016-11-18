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

def get_liked_posts(uid, **kwargs):
    offset = kwargs.get('offset', 0)

    posts_q = """SELECT t.*, Account.username
                FROM (
                    SELECT Posted.* FROM Posted, Liked
                    WHERE Posted.pid = Liked.post_id
                    AND Liked.liker_id = %s
                    ORDER BY time_created DESC OFFSET {} LIMIT 20
                ) AS t
                INNER JOIN Account
                ON t.uid = Account.uid
                """.format(offset)

    cursor = g.conn.execute(posts_q, (uid,))
    posts = [{
            'pid': result[0],
            'replyto': result[1],
            'uid': result[2],
            'date': datetime.strftime(result[3], "%b %d"),
            'content': result[4],
            'username': result[5]
          } for result in cursor]

    for post in posts:
        post['likes'] = get_likes_count_for_post(post['pid'])

    cursor.close()

    return posts

def get_user_from_post(pid):
    if pid is None:
        return None
    user_q="""SELECT Posted.uid FROM Posted WHERE Posted.pid=%s"""
    cursor=g.conn.execute(user_q, (pid))
    reply=[result[0] for result in cursor]
    finalVal=str((find_username_from_user(reply[0]))[0])
    cursor.close()
    return finalVal

def delete_post(pid):
    delete_q="""DELETE FROM Posted WHERE Posted.pid=%s"""
    cursor=g.conn.execute(delete_q, (pid))
    cursor.close()

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
    user_q = "SELECT * FROM Account WHERE username = %s"
    cursor = g.conn.execute(user_q, (username.lower(),))
    user = [result[0] for result in cursor]

    cursor.close()

    return (len(user) > 0)

def insert_user(username, email, password_hash):
    reserved = ["login", "signup", "api", "messages", "logout"]

    if username_exists_in_db(username) or username.lower() in reserved:
        return

    insert_q = """INSERT INTO
                Account (time_created, username, email, password)
                VALUES (current_timestamp, %s, %s, %s)"""
    g.conn.execute(insert_q, (username.lower(), email, password_hash))

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

def get_uid_from_username(username):
    user_q = """SELECT uid FROM Account WHERE username = %s"""
    cursor = g.conn.execute(user_q, (username.lower(),))
    user = [result for result in cursor]
    cursor.close()

    if len(user) != 1:
        raise RuntimeError

    return user[0][0] # why

def find_username_from_user(uid):
    user_q="""SELECT Account.username FROM Account WHERE Account.uid=%s"""
    cursor=g.conn.execute(user_q, (uid))
    val=[result[0] for result in cursor]
    return val


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

def is_following(username, uid):
    """
    does {username} follow {uid}
    """
    if not username or not uid:
        return False

    u1 = get_uid_from_username(username)

    follow_q = """SELECT Count(*) FROM Followed
                WHERE Followed.follower_id = %s
                AND Followed.subject_id = %s"""

    cursor = g.conn.execute(follow_q, (u1, uid))
    (f,) = cursor.fetchone()

    return not not f

def follow(u1, u2):
    """
    params are both usernames
    """
    if is_following(u1, get_uid_from_username(u2)):
        return

    u1 = get_uid_from_username(u1)
    u2 = get_uid_from_username(u2)

    insert_q = """INSERT INTO Followed
                VALUES (%s, %s, current_timestamp)"""

    g.conn.execute(insert_q, (u1, u2))


###############################
#
#    CHANNEL QUERIES
#
###############################

def create_channel(name, admin_id, description):
    channel_q="""INSERT INTO Channel (name, admin_id, description) VALUES (%s, %s, %s)"""
    g.conn.execute(channel_q, (name, admin_id, description))

def get_memberships_of_uid(uid):
    channel_q = """SELECT Channel.name FROM Channel, Membership
           WHERE Membership.gid = Channel.gid
           AND Membership.uid = %s"""

    cursor = g.conn.execute(channel_q, (uid,))
    channels = [result[0] for result in cursor]
    cursor.close()

    return channels

def get_description(channel_name):
    channel_q = """SELECT Channel.description FROM Channel
                    WHERE Channel.name = %s"""

    cursor = g.conn.execute(channel_q, (channel_name,))
    (d,) = cursor.fetchone()
    cursor.close()

    return d

def is_member(username, channel_name):
    if not username or not channel_name:
        return False

    channel_q = """SELECT Count(*) FROM Membership
                    WHERE Membership.uid = 
                    (
                        SELECT Account.uid
                        FROM Account
                        WHERE Account.username = %s
                    )
                    AND Membership.gid = 
                    (
                        SELECT Channel.gid
                        FROM Channel
                        WHERE Channel.name = %s
                    )"""

    cursor = g.conn.execute(channel_q, (username, channel_name))
    (d,) = cursor.fetchone()
    cursor.close()

    return not not d

def get_memberships_for_channel(channel_name):
    channel_q = """SELECT Account.username
                FROM (
                    SELECT Channel.*, Membership.*
                    FROM Channel, Membership
                    WHERE Channel.gid = Membership.gid
                    AND Channel.name = %s
                ) AS t
                JOIN Account
                ON Account.uid = t.uid"""

    cursor = g.conn.execute(channel_q, (channel_name,))

    members = [result[-1] for result in cursor]

    cursor.close()

    return members

def get_posts_for_channel(channel_name, **kwargs):
    offset = kwargs.get('offset', 0)

    posts_q = """SELECT Posted.*, Account.username
                FROM Posted
                JOIN Account
                ON Account.uid = Posted.uid
                WHERE Posted.uid IN
                (
                    SELECT Account.uid
                    FROM Account, Membership
                    WHERE Account.uid = Membership.uid
                    AND Membership.gid = 
                    (
                        SELECT Channel.gid
                        FROM Channel
                        WHERE Channel.name = %s
                    )
                )
                ORDER BY Posted.time_created DESC
                OFFSET {} LIMIT 20""".format(offset)

    cursor = g.conn.execute(posts_q, (channel_name,))

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

def join_channel(member, channel):
    uid = get_uid_from_username(member)
    print uid

    q = """SELECT gid FROM Channel WHERE name = %s"""
    cursor = g.conn.execute(q, (channel,))
    (gid,) = cursor.fetchone()

    insert_q = """INSERT INTO Membership
                    VALUES (%s, %s)"""
    g.conn.execute(insert_q, (uid, gid))

def get_channel_admin(channel_name):
    q = """SELECT Account.username FROM Account, Channel
            WHERE Account.uid = Channel.admin_id
            AND Channel.gid = 
            (
                SELECT Channel.gid
                FROM Channel
                WHERE lower(Channel.name) = %s
            )"""

    cursor = g.conn.execute(q, (channel_name.lower(),))
    (admin_name,) = cursor.fetchone()
    cursor.close()

    return admin_name

def delete_channel(channel_name):
    q = "DELETE FROM Channel WHERE lower(Channel.name) = %s"
    g.conn.execute(q, (channel_name.lower(),))


###############################
#
#    LIKE QUERIES
#
###############################

def does_user_like_post(username, pid):
    uid = get_uid_from_username(username)

    if not uid:
        return False

    like_q = """SELECT * FROM Liked
                WHERE Liked.liker_id = %s
                AND Liked.post_id = %s"""

    cursor = g.conn.execute(like_q, (uid, pid))

    likes = [result[0] for result in cursor]
    cursor.close()

    return not not likes

def like_post(username, pid):
    uid = get_uid_from_username(username)

    insert_q = """INSERT INTO Liked (liker_id, timestamp, post_id)
                VALUES (%s, current_timestamp, %s)"""

    g.conn.execute(insert_q, (uid, pid))

def unlike(username, pid):
    uid = get_uid_from_username(username)

    delete_q = """DELETE FROM Liked
                WHERE Liked.liker_id = %s
                AND Liked.post_id = %s"""

    g.conn.execute(delete_q, (uid, pid))

def get_num_likes_for_uid(uid):
    likes_q = """SELECT Count(*) FROM Liked
                WHERE Liked.liker_id = %s"""

    cursor = g.conn.execute(likes_q, (uid,))
    (num_rows,)=cursor.fetchone()
    cursor.close()

    return num_rows

def get_likes_for_post(pid):
    post_q="""SELECT Liked.liker_id FROM Liked WHERE Liked.post_id=%s"""
    cursor=g.conn.execute(post_q, (pid))
    likes=[]
    for result in cursor:
        likes.append(find_username_from_user(result[0]))

    cursor.close()
    return likes


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
    sender_id=find_user_from_username(username)['uid']
    recipient_id=find_user_from_username(recipient)['uid']
    if recipient_id == None:
        return None
    user_q="""INSERT INTO sent_message (sender_id, recipient_id, sent_time, content)
                VALUES (%s, %s, current_timestamp, %s)"""
    
    cursor=g.conn.execute(user_q, (sender_id, recipient_id, content))
    cursor.close()
    return recipient_id

def add_post(replyto, username, content):
    poster_id=find_user_from_username(username)['uid']
    if replyto is None:
        user_q="""INSERT INTO Posted (uid, time_created, content)
                VALUES (%s, current_timestamp, %s)"""
        cursor=g.conn.execute(user_q, (poster_id, content))
    else:
        user_q="""INSERT INTO Posted (replytoid, uid, time_created, content)
                VALUES (%s, %s, current_timestamp, %s)"""
        cursor=g.conn.execute(user_q, (replyto, poster_id, content))
    
    pid_q="""SELECT MAX(pid) FROM Posted"""
    cursor=g.conn.execute(pid_q)
    pid=[result[0] for result in cursor]
    cursor.close()
    return pid

def get_post(pid):
    user_q="""SELECT Posted.* FROM Posted WHERE Posted.pid=%s"""
    cursor=g.conn.execute(user_q, (pid))
    for result in cursor:
        posts = {
                'pid': result[0],
                'replyto': result[1],
                'uid': result[2],
                'date': datetime.strftime(result[3], "%b %d"),
                'content': result[4]
              }
    cursor.close()
    return posts



##############################
#
#    NOTIFICATION QUERIES
#
##############################

def get_notifications_for_user(username, **kwargs):
    offset = kwargs.get('offset', 0)

    uid = get_uid_from_username(username)

    notif_q = """SELECT Receive_notification.*
                 FROM Receive_notification, Account
                 WHERE Receive_notification.recipient_id = Account.uid
                 AND Account.uid = %s
                 ORDER BY Receive_notification.time_created DESC
                 OFFSET {} LIMIT 20""".format(offset)

    cursor = g.conn.execute(notif_q, (uid,))
    results = [{
        'nid': result[0],
        'date': datetime.strftime(result[2], "%b %d"),
        'seen': result[3],
        'description': result[4]
    } for result in cursor]
    cursor.close()

    return results

def num_notifications_for_user(username):
    q = """SELECT Count(*) FROM Receive_notification
            WHERE Receive_notification.recipient_id =
            (
                SELECT uid FROM Account
                WHERE Account.username = %s
            )
            AND Receive_notification.seen = 'false'"""

    cursor = g.conn.execute(q, (username,))
    (num_not,) = cursor.fetchone()
    cursor.close()

    return num_not

def clear_notification(nid):
    q = """UPDATE Receive_notification
            SET seen = true
            WHERE nid = %s"""

    g.conn.execute(q, (nid,))

def like_notification(username, pid):
    # first, find notification target
    target_q = """SELECT Account.uid
                  FROM Account, Posted
                  WHERE Account.uid = Posted.uid
                  AND Posted.pid = %s"""
    cursor = g.conn.execute(target_q, (pid,))
    (target,) = cursor.fetchone()
    (target_username,) = find_username_from_user(target)

    description = """
        <span class="link-wrapper"><a class="inline-link" href="/{}">@{}</a></span>
            liked your
        <span class="link-wrapper"><a class="inline-link" href="{}/{}">post</a></span>
    """.format(username, username, target_username, pid)

    q = """INSERT INTO
            Receive_notification (recipient_id, time_created, seen, description)
            VALUES (%s, current_timestamp, %s, %s)"""
    g.conn.execute(q, (target, False, description))

def message_notification(username, target):
    u2 = get_uid_from_username(target)

    description = """
        <span class="link-wrapper"><a class="inline-link" href="/{}">@{}</a></span>
            sent you a message. view
        <span class="link-wrapper"><a class="inline-link" href="/messages">here</a></span>
    """.format(username, username)

    q = """INSERT INTO
            Receive_notification (recipient_id, time_created, seen, description)
            VALUES (%s, current_timestamp, %s, %s)"""
    g.conn.execute(q, (u2, False, description))

def follow_notification(username, target):
    u2 = get_uid_from_username(target)

    description = """
        <span class="link-wrapper"><a class="inline-link" href="/{}">@{}</a></span>
            followed you :^)
    """.format(username, username)

    q = """INSERT INTO
            Receive_notification (recipient_id, time_created, seen, description)
            VALUES (%s, current_timestamp, %s, %s)"""
    g.conn.execute(q, (u2, False, description))

