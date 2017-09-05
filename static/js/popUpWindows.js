function popupCaseDetails(evt) {
    case_action = evt.currentTarget.id;
    caseID = evt.currentTarget.value;
    console.log(caseID);
    var params = 'scrollbars=yes,resizable=yes,status=no,location=no,toolbar=no,menubar=no,width=900,height=600,left=-1000,top=-1000';

    window.open('/case-'+case_action+'/'+caseID, 'Case ' + case_action, params)
}

$('#settings').on('click', popupCaseDetails)
$('#messages').on('click', popupCaseDetails)