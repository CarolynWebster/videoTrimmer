function validateRegistration(evt) {
    evt.preventDefault()

    //make sure the provided passwords match
    if ($('#pass').val() != $('#passC').val()){
        $('#error-log').html("Passwords don't match")
    }
    // make sure they provided an email address
    else if ($('#email').val().indexOf('@') == -1) {
        $('#error-log').html("Please enter a valid email address")
    }
    //if all good - post away!
    else{
        var formValues = $("#register-user").serialize();
        $.post('/register', formValues, function(result){
            if (result === "Success"){
                window.location='/cases'
            }
        })
    }

}

$('#submit-btn').on('click', validateRegistration)