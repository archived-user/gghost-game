'use strict';

function displayError(code) {
  
  var error = "";
  switch (code) {
    // display player role and words
    case '00':
      // missing game
      error = "4Oh4 Game Not Found!";
      break;
    case '01':
      // game full
      error = "Sorry. Fullstack.";
      break;
    case '02':
      // game ended
      error = "Game Ended. GG!";
      break;
    default:
      // all other codes does nothing
      return;
  }
  
  $( document ).ready(function() {
    console.log( error );
    $('#notice').text(error).fadeIn(500).delay(2000).fadeOut(500); 
  });
}