function deleteUser(evt){
    var confirm_delete = confirm("Are you sure you want to remove this user? This action cannot be undone.");

    if (confirm_delete === true){
        var user = evt.currentTarget.id;
        var formInputs = {
            'del_user': user,
            'case_id': currCaseID,
        };
        $.post('/remove-usercase', formInputs, function(results) {
            //get id for tr holding that user
            var user_row = "#User_" + user;
            $(user_row).remove();
            // console.log(results)
        });
    }

}

$('.remove-user-x').on('click', deleteUser);


function updateUsers (){
    var new_users = $('#new_users_input').val();
    console.log(new_users);
    var formInputs = {
        'new_users': new_users,
        'case_id': currCaseID,
    };
    console.log('clicked');
    $.post('/add-usercase', formInputs, function (results) {
        //refresh the page after adding users
        $('#user-table').append(results);
        $('.new-user-x').on('click', deleteUser);
        $('#new_users_input').val('');
    });
}

$('#add_users').on('click', updateUsers);