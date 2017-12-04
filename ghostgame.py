# Based off the sample game from GCP-Firebase demo
# https://github.com/GoogleCloudPlatform/python-docs-samples/tree/master/appengine/standard/firebase/firetactoe
"""Ghost Game with the Firebase API"""

import base64
try:
    from functools import lru_cache
except ImportError:
    from functools32 import lru_cache
import json
import os
import re
import time
import urllib
import random
import logging

import httplib2
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from google.appengine.api import app_identity
from google.appengine.ext import ndb
from oauth2client.client import GoogleCredentials


_FIREBASE_CONFIG = '_firebase_config.html'
_IDENTITY_ENDPOINT = ('https://identitytoolkit.googleapis.com/'
                      'google.identity.identitytoolkit.v1.IdentityToolkit')
_FIREBASE_SCOPES = ['https://www.googleapis.com/auth/firebase.database',
                    'https://www.googleapis.com/auth/userinfo.email']
_ROLES = ["major","minor","ghost", "clown"]
_RATIOS = { 6: (3,1,1,1),
            7: (4,1,1,1),
            8: (4,2,1,1),
            9: (5,2,1,1),
           10: (6,2,1,1) }
_LIFETIME = 60

app = Flask(__name__)
# Set the flask session secret key.
app.secret_key = '******************************'


# Memoize the value, to avoid parsing the code snippet every time
# @lru_cache is a decorator to wrap a function with a memoizing callable that saves up to the MAXSIZE most recent call (Least Recently Used algo)
# in this specific use case, the cache hit-rate is 1 as the output of this function is always the same.
@lru_cache()
def _get_firebase_db_url():
    """Grabs the databaseURL from the Firebase config snippet. Regex looks
    scary, but all it is doing is pulling the 'databaseURL' field from the
    Firebase javascript snippet"""
    regex = re.compile(r'\bdatabaseURL\b.*?["\']([^"\']+)')
    cwd = os.path.dirname(__file__)
    try:
        with open(os.path.join(cwd, 'templates', _FIREBASE_CONFIG)) as f:
            url = next(regex.search(line) for line in f if regex.search(line))
    except StopIteration:
        raise ValueError(
            'Error parsing databaseURL. Please copy Firebase web snippet '
            'into templates/{}'.format(_FIREBASE_CONFIG))
    return url.group(1)

# Memoize the authorized http, to avoid fetching new access tokens
@lru_cache()
def _get_http():
    """Provides an authed http object."""
    http = httplib2.Http()
    # Use application default credentials to make the Firebase calls
    # https://firebase.google.com/docs/reference/rest/database/user-auth
    creds = GoogleCredentials.get_application_default().create_scoped(
        _FIREBASE_SCOPES)
    creds.authorize(http)
    return http

def _send_firebase_message(u_id, message=None):
    """Updates data in firebase. If a message is provided, then it updates
    the data at /channels/<channel_id> with the message using the PATCH
    http method. If no message is provided, then the data at this location
    is deleted using the DELETE http method
    """
    url = '{}/{}.json'.format(_get_firebase_db_url(), u_id)
    if message:
        return _get_http().request(url, 'PATCH', body=message)
    else:
        return _get_http().request(url, 'DELETE')


# Create logs for convenient debugging in dev server.
def bp(num):
    logging.info('[BREAKPOINT]')
    logging.info(num)
    return

# Create info logs visible in GCP management console.
def logG(message):
    logging.info("[GAME]:")
    logging.info(message)

def logA(message):
    logging.info("[APP]:")
    logging.info(message)

# TODO Implement checker to check if properties exist before accessing
# session properties.


### GAME MODELS AND LOGIC ###

# Player object that represents each player CONNECTED to the game
# via Firebase open channel.
class Player(ndb.Model):
    # Instance id = username
    major = ndb.StringProperty()
    minor = ndb.StringProperty()
    role = ndb.StringProperty(default="major")
    diff = ndb.IntegerProperty(default=9)

# Game object that represents the game room.
# Identified by Game ID from player login page.
class Game(ndb.Model):
    # Instance id = gid
    # players: list of players currently CONNECTED.
    player1 = ndb.StringProperty(default=None)
    players = ndb.StringProperty(repeated=True)
    started = ndb.BooleanProperty(default=False)
    
    def firebase_update(self, major="", minor="", seq="", **lobby):
        """Updates Firebase with key information.
        By default registers Firebase with a single player
        with all other information set as empty.
        """
        payload = { "words" : { "major" : major, "minor" : minor, "seq" : seq},
                    "lobby" : lobby }
        message = json.dumps(payload)
        _send_firebase_message(self.key.id(), message=message)
        return
    
    def clear_player(self, username):
        """Remove a player from Game.
        Delete the corresponding player record from Firebase.
        Delete the corresponding Player object.
        """
        if username in self.players:
            self.players.remove(username)
            _send_firebase_message(self.key.id() + "/lobby/" + username)
            player = Player.get_by_id(username)
            if player:
                player.key.delete()
            self.put()
            logG("Removed Player <" + username + ">")
        return
    
    def clear_all(self):
        """Delete the entire Firebase tree corresponding to the Game id.
        Delete all Player objects corresponding to the Game.
        Delete the Game object itself.
        """
        _send_firebase_message(self.key.id())
        for each in self.players:
            player = Player.get_by_id(each)
            if player:
                player.key.delete()
        logG("Delete Game <" + self.key.id() + ">")
        self.key.delete()
        return
    
    def players_dict(self):
        """Returns a dictionary with all players as
        individual keys with empty values.
        """
        d = {}
        if self.players:
            for username in self.players:
                d[username] = ""
        return d
    
    def is_player1(self, username):
        """Returns True if player is first player."""
        return self.player1 == username
    
    def has_player(self, username):
        """Returns True if player has joined the game."""
        if username in self.players:
            return True
        return False
    
    def count_players(self):
        """Returns number of players in the game."""
        count = 0
        if self.players:
            count = len(self.players)
        return count
    
    def is_full(self):
        """Returns True if game had started
        or if maximum number of players had joined game.
        """
        return self.started or self.count_players == 10


### FLASK SERVER LOGIC ###

# [BEFORE FIRE REQUEST]
@app.before_first_request
def make_session_permanent():
    """Set session lifetime to 31 days."""
    session.permanent = True
    return

# [DEFAULT]
@app.route('/')
def default():
    return redirect(url_for('login', err='0'))

# [LOGIN]
@app.route('/login<err>', methods=['GET', 'POST'])
def login(err):
    """Serves the Login form 
    and saves player information in session
    """
    # POST request.
    if request.method == 'POST':
        for k,v in request.form.items():
            session[k] = v
        session['diff'] = int(session['diff'])
        return redirect(url_for('process', gid=session['gid']))    
    # GET request.
    if 'gid' in session:
        game = Game.get_by_id(session['gid'])
        if game:
            # Always perform the Logout logic.
            if game.is_player1(session['username']):
                game.clear_all()
            else:
                # If game had already started, player will merely AFK
                # and is able to login again to resume the game.
                if not game.started:
                    game.clear_player(session['username'])
    return render_template('login.html', code=err, **session) 

# [PROCESS]
@app.route('/process?gid=<gid>')
def process(gid):
    """Creates a Game Object and updates Firebase for the first time.
    Redirect the player to the game if game already exists.
    """
    game = Game.get_by_id(gid)
    if not game:
        logG("Creating New Game <" + gid + "> Player1 <" + session['username'] + ">")
        game = Game(id=gid)
        lobby = { session['username'] : "" }
        game.firebase_update(**lobby)
        game.player1 = session['username']
        game.put()
    else:
        if not game.has_player(session['username']):
            # Kick the player if game is already full.
            if game.is_full():
                return redirect(url_for('login', err='01'))
    return redirect(url_for('lobby', gid=game.key.id()))

# [LOBBY]
@app.route('/lobby?gid=<gid>')
def lobby(gid):
    """Serves the main game screen."""
    game = Game.get_by_id(gid)
    if not game:
        return redirect(url_for('login',err='00'))
    template_values = {
        'channel_id': gid,
        'me': session['username'],
        'first': game.is_player1(session['username']),
        'url': url_for('login', err='0')
    }
    return render_template('lobby.html', **template_values)

# [OPENED]
@app.route('/opened', methods=['POST'])
def opened():
    """Create Player object, update Game and Firebase state
    if player client successfully listens to Firebase.
    """
    game = Game.get_by_id(session['gid'])
    if not game:
        # Game is missing.
        return 'MISS'
    if game.has_player(session['username']):
        # Player already joined the game.
        return ('', 204)
    if game.is_full():
        # Game is full.
        return 'FULL'
    # Else create Player object.
    player = Player(id=session['username'],
                    major=session['major'],
                    minor=session['minor'],
                    diff=session['diff'])
    player.put()
    game.players.append(session['username'])
    game.put()
    lobby = game.players_dict()
    game.firebase_update(**lobby)
    return ('', 204)

# [START]
@app.route('/start')
def start():
    """Starts the game and update Firebase to relfect player roles."""
    game = Game.get_by_id(session['gid'])
    if not game:
        # Game is missing.
        return redirect(url_for('login', err='00'))
    if game.count_players() < 6:
        # Player somehow started game with insufficient players.   
        logG("Not Enough Players to Start Game")
        return ('', 204)
    
    # Start game.
    game.started = True
    game.put()
    size = game.count_players()
    logG("Started Game <" + game.key.id() + "> Players: <" + str(size) + ">")    
    
    # Assign roles to each player.
    lobby = {}
    player = None
    ghost_position = 9
    ghost_player = ""
    playerlist = list(game.players)
    random.shuffle(playerlist)
    rolelist = list(_ROLES)
    for num in _RATIOS[size]:
        currentrole = rolelist.pop(0)
        for count in xrange(num):
            username = playerlist.pop(0)
            player = Player.get_by_id(username)
            player.role = currentrole
            player.put()
            lobby[username] = currentrole
            if currentrole == "ghost":
                ghost_position = player.diff
                ghost_player = username
    
    # Generate the sequence of play, preserving the position
    # as requested by the ghost player.
    playerlist = list(game.players)
    playerlist.remove(ghost_player)
    random.shuffle(playerlist)
    playerlist.insert(ghost_position, ghost_player)
    payload = ""
    for i in xrange(size):
        username = playerlist.pop(0)
        if i == 10:
            payload = payload + "<div class=center><b>" + str(i+1) + ".</b>  " + username + "</div>"
        else:
            payload = payload + "<div class=center><b>" + str(i+1) + "</b>.   " + username + "</div>"
    logA("Payload: " + payload)
    
    # Send update to Firebase.
    game.firebase_update(major=player.major, minor=player.minor, seq=payload, **lobby)
    return ('', 204)