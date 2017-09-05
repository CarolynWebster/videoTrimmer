function collect_checked_vids(evt){
    // get the current time for the zip
    currTime = getCurrentTime();

    //uncheck all the boxes
    uncheckAll();
    
    showAlert();

    //get an array of all the checked clips
    var checked_vids = $('.vidcheck:checkbox:checked');
    var vidsToDL = [];
    for(var i = 0; i < checked_vids.length; i++){
        console.log(checked_vids[i].value);
        vidsToDL.push(checked_vids[i].value);
    }
    vids = vidsToDL.toString();
    console.log(vids);
    var formInputs = {
        'clips': vids,
        'vid_id': vidID,
        'call_func': evt.currentTarget.id,
        'vid_type': typeOfVid,
        'curr_time': currTime
    };

    var all_cboxes = $('.vidcheck:checkbox');
    all_cboxes.prop('checked', false);

    if (evt.currentTarget.id == 'stitchClips' |
        evt.currentTarget.id == 'downloadClips' |
        evt.currentTarget.id == 'createDeck') {
        console.log("handle-clips");
        //send direction to server
        //download function called from the handle-clips route
        $.post('/handle-clips', formInputs, function() {
            console.log('request complete');
            $('#success-message').fadeOut();
        });
    }
    else if (evt.currentTarget.id == 'deleteClips') {
        console.log("delete");
        var confirm_delete = confirm('Are you sure you want to delete '+checked_vids.length+' clips?\nThis action cannot be undone.');
        //send direction to server
        //delete function called from the handle-clips route
        if (confirm_delete === true){
            $.post('/handle-clips', formInputs, function() {
                console.log('request complete');
                $('#success-message').fadeOut();
                location.reload();
            });
        }
    }
}

// function collect_checked_vids(evt){

//     //get an array of all the checked clips
//     var checked_vids = $('.vidcheck:checkbox:checked');
//     var vidsToDL = [];
//     for(var i = 0; i < checked_vids.length; i++){
//         // console.log(checked_vids[i].value)
//         vidsToDL.push(checked_vids[i].value);
//     }
//     vids = vidsToDL.toString();
//     // console.log(vids)
//     var formInputs = {
//         'clips': vids,
//         'call_func': evt.currentTarget.id,
//         'vid_type': "video"
//     };

//     var all_cboxes = $('.vidcheck:checkbox');
//     all_cboxes.prop('checked', false);

//     if (evt.currentTarget.id == 'downloadClips') {
//         //send direction to server
//         //download function called from the handle-clips route
//         $.post('/handle-clips', formInputs, function() {
//         // console.log('request complete')
//         location.reload();
//         });
//     }
//     else if (evt.currentTarget.id == 'deleteClips') {
//         var confirm_delete = confirm('Are you sure you want to delete '+checked_vids.length+' clips?\nThis action cannot be undone.');
//         //send direction to server
//         //delete function called from the handle-clips route
//         if (confirm_delete === true)
//             $.post('/handle-clips', formInputs, function() {
//                 // console.log('request complete')
//                 location.reload();
//             });
//     }
// }

// function toggleChecks(evt) {
//     //get the status if the check mark
//     var status = evt.currentTarget.checked;
//     // collect all the checkboxes
//     var all_cboxes = $('.vidcheck:checkbox');
//     console.log(status);
//     // if the check all was true - check all boxes
//     if (status === true) {
//         all_cboxes.prop('checked', true);
//     }
//     // otherwise uncheck all
//     else {
//         all_cboxes.prop('checked', false);
//     }

// }

function toggleChecks(evt) {
    var status = evt.currentTarget.checked;
    console.log(status);
    var all_cboxes = $('.vidcheck:checkbox');
    if (status === true) {
        //all_cboxes.prop('checked', true);
        for (var c=0; c < all_cboxes.length; c++) {
            if (all_cboxes[c].offsetHeight > 0) {
                all_cboxes[c].checked = true;
            }
        }
    }
    else {
        all_cboxes.prop('checked', false);
    }

}

function uncheckAll() {
    //get all the checkboxes
    checkboxes = $('.cbox');
    checkboxes.prop('checked', false);
}

$('#stitchClips').on('click', collect_checked_vids);
$('#downloadClips').on('click', collect_checked_vids);
$('#deleteClips').on('click', collect_checked_vids);
$('#createDeck').on('click', collect_checked_vids);
$('#select-all').on('change', toggleChecks);
