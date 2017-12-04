'use strict';

function initGame(me, channelId, first, url) {

  var channel = null;
  var lobby = null;
  var words = null;
  var player1 = false;

  /**
   * This method lets the server know that the user has opened the channel
   */
  function onOpened() {
    $.post('/opened', function(data, status) {
      console.log("Data: " + data + "\nStatus: " + status + "\nUrl:" + url);
      if (data === "FULL") {
      	channel.off()
    	window.location.replace("https://" + window.location.hostname + url + "1");
    	return;
      }
      if (data === "MISS") {
      	channel.off()
    	window.location.replace("https://" + window.location.hostname + url + "0");
    	return;
      }
    }, "text");
  }

  /**
   * This method is called every time an event is fired from Firebase
   */
  function onMessage(tree) {
    //console.log(tree);
    if (tree === null) {
    	// game has been killed
    	console.log("Game Missing. Sad :(");
    	window.location.replace("https://" + window.location.hostname + url + "2");
    	return;
    }
    lobby = tree['lobby'];
    words = tree['words'];
    console.log(tree);
    
    if (words['major'].length > 0) {
      // [GAME STARTED]
      
      // hide leave game, insufficient players, start game buttons
      $( ".started" ).css( "display", "none" );
      // display player profile
      $('#infoheader').append(me);
      // display sequence of play
      $('#header').empty();
      $('#header').append("Sequence of Play");
      $('#lobbylist').empty();
      $('#lobbylist').append(words['seq']);
      
      if (player1) {
      	// player 1 End Game button
      	$('#endbutton').attr("hidden", false);
      }
      if (lobby.hasOwnProperty(me) === false) {
      	// if somehow player managed to view the lobby but did not technically joined game
      	console.log("Fullstack, Without You. Sad :(");
      	window.location.replace("https://" + window.location.hostname);
      	return;
      } 
      switch (lobby[me]) {
      	// display player role and words
      	case 'major':
      	  $('#info').append('<div class=center>Role: <b>Villager</b></div>');
      	  $('#info').append('<div class=center><i>'+ words['major'] + '</i></div>');
    	  break;
    	case 'minor':
    	  $('#info').append('<div class=center>Role: <b>Villager</b></div>');
          $('#info').append('<div class=center><i>'+ words['minor'] + '</i></div>');
    	  break;
        case 'ghost':
          $('#info').append('<div class=center>Role: <b>Ghost</b></div>');
    	  break;
    	case 'clown':
          $('#info').append('<div class=center>Role: <b>Clown</b></div>');
          $('#info').append('<div class=center><i>'+ words['major'] + '</i></div>');
          $('#info').append('<div class=center><i>'+ words['minor'] + '</i></div>');
    	  break;
      }
    } else {
      // [GAME NOT STARTED]
      
      // display all players who joined game
      $('#lobbylist').empty();
      for (var name in lobby) {
        if (lobby.hasOwnProperty(name)) {
          $('#lobbylist').append('<div class=center><b>' + name + '</b></div>');
        }
      }
      var lobbykeys = Object.keys(lobby);
      if (lobbykeys.length > 5) {
      	// if players exceeded minimum 6
      	$('#emptybutton').attr("hidden", true);
      	if (player1) {
      		// player 1 Start Game button
      		$('#startbutton').attr("hidden", false);
      	}
      } else {
      	// else cannot start game
      	$('#emptybutton').attr("hidden", false);
      	$('#startbutton').attr("hidden", true);
      }
    }    
  }

  function openChannel() {
    // setup a database reference at path /channelId
    channel = firebase.database().ref(channelId);
    // add a listener to the path that fires any time the value of the data changes
    channel.on('value', function(dataSnapshot) {
      onMessage(dataSnapshot.val());
    });
    
    // let the server know that the channel is open
    onOpened();
  }

  function initialize() {
  	if (first == "True") {
      player1 = true;
    }
    
    openChannel();
  }

  setTimeout(initialize, 100);
}