# Ghost Game, using Flask and Firebase, on App Engine
___

## The Game
A party game for 6 to 10 players. (To be played in person! This application merely facilitates the game.)

The game consists of 3 roles: **Clown, Ghost, Villager**. The server will randomly assign the roles to each player and are kept secret. Every game will only have 1 Clown and 1 Ghost. All Villagers belong to the same faction and must work together to identify the Ghost in order to win the game. The Ghost and the Clown belongs to the same opposing faction and must help each other to achieve victory.

* The **Villager**: When the game begins, each Villager will be given a word. This word is to be kept secret and known only to the Villager.
* The **Ghost**: When the game begins, the Ghost will be given nothing. The Ghost is supposed to guess what is the secret word that the Villagers possess.
* The **Clown**: When the game begins, the Clown will receive a pair of words. The objective of the Clown is to distract other Villagers and draw attention and suspicions away from the Ghost.

The gameplay consists of multiple rounds. In each round the players will announce a hint / comment / description about the word they are given, without divulging the word itself. The players take turns according to the sequence of play generated by the server. After all players have their turn, everyone will vote to elimiate one player, who is most likely to be the Ghost, from the game. The game will proceed to the next round with one less player if the Villagers fail to identify the Ghost.

_Victory Conditions_:
* At any point in the game, the Ghost may announce its identity to end the game and guess the word. Correct guess results in Ghost victory.
* If the Clown gets voted out of the game, the game ends and the Clown achieves victory.
* If the Ghost gets voted out of the game, the game ends and the Villagers achieve victory.

**Using the application**:

On the landing page, every player must enter their username, game id, majority and minority words, as well as the difficulty.
The game id will determine the room that the player connects to, so all players should be submiting the same id. The majority and minority words will be the secret words of the game to be distributed to all the Villagers if the input player gets selected as the Clown. The difficulty level will determine the position of the Ghost in the sequence of play if the input player gets selected as the Ghost.

After submitting the information, players will enter a lobby while waiting for sufficient players to start the game. Once the minimum of 6 players have joined the lobby, the first player in the lobby will be provided an option to start the game.

Once the game begins, the players themselves will have to regulate the flow of the game. The same first player will have the option to end the game and bring everyone back to the landing page.

___

## Setup

* Set up an empty Python app in Google App Engine, Standard Environment.
* Set up a Firebase project and import the Google project associated with your Python app.
* Clone the repository using Google Cloud Shell. (For simplicity, I recommend running your tests on a development server on Google Cloud Shell, instead of your local environment)
* In the Overview section on Firebase console, click 'Add Firebase to your web app' and replace the
  contents of the file
  [`templates/_firebase_config.html`](templates/_firebase_config.html) with the
  given snippet. This provides credentials for the javascript client to read from Firebase.
* In the gghostgame.py file, set the session secret key.

### Install dependencies

Before running or deploying this application, install the dependencies using
[pip](http://pip.readthedocs.io/en/stable/):

    pip install -t lib -r requirements.txt

## Application

### Test application
To test the application on a development server, run the command in the project root:

    dev_appserver.py app.yaml

### Deploy application
To deploy the application, run the command:

    gcloud app deploy app.yaml

___

## Resources

Helpful resources that made this application possible:

* Building a Firebase application on App Engine - https://cloud.google.com/solutions/using-firebase-real-time-events-app-engine
* Test the speed of the webpage - https://developers.google.com/speed/pagespeed/
* Managing authenticated users in Firebase - https://github.com/firebase/functions-samples/tree/master/delete-unused-accounts-cron
* Test your Javascript - https://jsfiddle.net
* Android-style toast notification using CSS - https://stackoverflow.com/questions/17723164/show-an-android-style-toast-notification-using-html-css-javascript
* Debugging link previews (specified by Open Graph) - http://iframely.com/debug