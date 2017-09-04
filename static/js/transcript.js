function showScript(evt) {
    vid_id = evt.currentTarget.id;

    var params = 'scrollbars=yes,resizable=yes,status=no,location=no,toolbar=no,menubar=no,width=900,height=600,left=-1000,top=-1000';

    window.open('/show-transcript/'+vid_id, 'Transcript', params)
}

function addScript(evt) {
    vid_id = evt.currentTarget.id;

    var params = 'scrollbars=yes,resizable=yes,status=no,location=no,toolbar=no,menubar=no,width=900,height=600,left=-1000,top=-1000';

    window.open('/add-transcript/'+vid_id, 'Add Transcript', params)
}

$('.tscriptTrue').on('click', showScript)
$('.tscriptFalse').on('click', addScript)

