$(document).ready(function() {
  var sock = new io.Socket('chat.support-local.allizom.org');
  sock.on('connect', function() {
  });
  sock.on('message', function(data) {
      var msg = $('<div></div>');
      $(msg).text(data);
      $('#messages').append(msg);
  });
  sock.connect();
  $('#sender').click(function(e) {
      e.preventDefault();
      sock.send($('#msg').val());
      $('#msg').val('');
      return false;
  });
});
