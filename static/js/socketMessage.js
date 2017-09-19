var socket;

function sendCaseMessage(evt){
    var new_mess = $('#new-message').val();

    $('#new-message').val("");

    // var formInputs = {
    //     'new_mess': new_mess,
    //     'case_id': currCaseID,
    // }
    // $.post('/send-casemessage', formInputs, function (results) {
    //     console.log('message sent!');
    // });
    var formInputs = {
        'new_mess': new_mess,
        'case_id': currCaseID,
    };
    var to_send = JSON.stringify(formInputs);
    console.log(to_send);
    socket.emit('send-casemessage', to_send);
}

function showNewMessage(results){
    $('#new-message').html("");

    mess_html = '<div class="case-mess" id="div_' + results.mess_id + '">';
    //add a remove button for the user who sent it
    if (results.user_id == currUser){
        mess_html = mess_html + '<button class="mess-remove close" id=' + results.mess_id + ' aria-label="Close"><span aria-hidden="true">&times;</span></button>';
    }
    mess_html = mess_html +  '<strong>' + results.user_name + '</strong> </br>' + results.mess_text + '</div>';

    $('#all-messages').prepend(mess_html);
    $('#'+results.mess_id).on('click', removeMessage);
}

$('#send-message').on('click', sendCaseMessage);


function removeMessage(evt){
    var mess_target = evt.currentTarget.id;

    var formInputs = {
        'mess_id': mess_target,
    };

    $.post('/remove-casemessage', formInputs, function (results) {
        // console.log("removed")
    });
}

function startChat(){
    var chatData = {
        'case_id': currCaseID,
    };
    
    var to_send = JSON.stringify(chatData);

    socket = io.connect('http://' + document.domain + ':' + location.port + '/chat');
    socket.on('connect', function() {
        socket.emit('join', to_send);
    });

    socket.on('new casemessage', function(results){
        console.log(results);
        showNewMessage(results);
    });

    socket.on('remove casemessage', function(results){
        console.log(results);
        $('#div_'+results).remove();
    });
}

startChat();

$(".mess-remove").on('click', removeMessage);