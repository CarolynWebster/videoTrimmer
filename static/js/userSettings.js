function addInputFields(){
        var editableFields = $('.is-editable');
        for (var i=0; i < editableFields.length; i++) {
            var fieldID = editableFields[i].id;
            var prev_content = "";
            if (fieldID != 'pass'){
                prev_content = editableFields[i].innerHTML;
            }
            var inputType = 'text';
            if (fieldID == 'email'){
                inputType = 'email';
            }
            if (fieldID == 'pass'){
                inputType = 'password';
            }
            editableFields[i].innerHTML = "<input id='input_" + fieldID + "' type='"+inputType+"' name='" + fieldID+ "' value='" + prev_content + "' autocomplete='new-password'>";
        }
        $('#submit-btn').show();
    }

    function sendUpdates(evt){
        evt.preventDefault();
        //get input info

        formInputs = {
            'user_id': userID,
            'email': $('#input_email').val(),
            'fname': $('#input_fname').val(),
            'lname': $('#input_lname').val(),
            'pass': $('#input_pass').val()
        };
        console.log(formInputs);
        $.post('/user-settings', formInputs, function(result) {
            console.log(result);
            if (result === "Success"){
                removeInputs();
                showAlert();
            }
            else{
                alert("You can't update another user's information");
            }
        });
    }

    function removeInputs(){
        console.log("remove");
        $('#submit-btn').hide();
        $('#email').html($('#input_email').val());
        $('#fname').html($('#input_fname').val());
        $('#lname').html($('#input_lname').val());
        $('#pass').html("*****");
    }

    function addInputField(evt){
        //get the name of the btn that was clicked
        var btnClicked = evt.currentTarget.id;
        // strip the change- prefix
        var spanID = btnClicked.replace("change-", "");
        console.log(spanID);
        // set up a jquery obj for the span
        var spanTarget = $('#'+spanID);
        // if we haven't added inputs yet
        if (spanTarget.hasClass('not-editing')){
            spanTarget.removeClass('not-editing');
            spanTarget.addClass('are-editing');
            var inputID = 'new-'+spanID;
            spanTarget.html("<input type='text', id='"+inputID+"'>");
        }
        else if (spanTarget.hasClass('are-editing')){
            console.log("here");
            var newInfo = $('#new-'+spanID).val();
            var formInputs = {
                'user_id': userID,
                'update_type': spanID,
                'updated_info': newInfo
            };
            console.log(formInputs);
            //send the update to the server
            $.post('/user-settings', formInputs, function(result) {
                console.log(result);
                if (result === "Success"){
                    showAlert();
                    //spanTarget;
                }
                else{
                    alert("You can't update another user's information");
                }
            });
        }
    }
    $('#edit-settings').on('click', addInputFields);
    $('#user-settings').on('submit', sendUpdates);
    $('.update-info').on('click', addInputField);