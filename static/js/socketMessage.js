function sendCaseMessage(evt){
    var new_mess = $('#new-message').val()

    var formInputs = {
        'new_mess': new_mess,
        'case_id': currCaseID,
    }
    $.post('/send-casemessage', formInputs, function (results) {
        console.log('message sent!')
    });

}

function showNewMessage(results){
    $('#new-message').html("")

    mess_html = '<div class="case-mess" id="div_' + results.mess_id + '">'
    //add a remove button for the user who sent it
    if (results.user_id == currUser){
        mess_html = mess_html + '<button class="mess-remove close" id=' + results.mess_id + ' aria-label="Close"><span aria-hidden="true">&times;</span></button>'
    }
    mess_html = mess_html +  '<strong>' + results.user_name + '</strong> </br>' + results.mess_text + '</div>'

    $('#all-messages').prepend(mess_html)
    $('#'+results.mess_id).on('click', removeMessage)
}

$('#send-message').on('click', sendCaseMessage)


function removeMessage(evt){
    var mess_target = evt.currentTarget.id

    var formInputs = {
        'mess_id': mess_target,
    };

    $.post('/remove-casemessage', formInputs, function (results) {
        // console.log("removed")
    });
}

$(".mess-remove").on('click', removeMessage)