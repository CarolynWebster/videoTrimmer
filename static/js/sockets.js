function check_file_updates() {
    // processing_clips = $('.clip-processing');
    // console.log(processing_clips);
    // clips_to_update = {};
    // clips_to_update.clips = [];
    // for (var i = 0; i < processing_clips.length; i++){
    //     var clip_id = processing_clips[i].id;
    //     clip_id = clip_id.replace("_Status", "");
    //     clips_to_update.clips.push(parseInt(clip_id));
    // }
    // var to_send = JSON.stringify(clips_to_update);

    var socket = io.connect('http://' + document.domain + ':' + location.port);
    // socket.on('connect', function() {
    //     socket.emit('update_clips', to_send);
    // });
    socket.on('server update', function(results){
        console.log("results", results['clips']);
        var clip_id = results['clips'][0];
        var start_at = results['clips'][1];
        var end_at = results['clips'][2];
        if (start_at.length > 8 || end_at.length > 8){
            start_at = start_at.substring(0, 8);
            end_at = end_at.substring(0, 8);
        }
        var sTime = strToDate(start_at);
        var eTime = strToDate(end_at);
        var diff = eTime - sTime;
        var duration = msToTime(diff);
        console.log(clip_id + " : " + start_at  + " : " + end_at);
        console.log(sTime, eTime, diff, duration);
        $('#' + clip_id + "_Status").html("Ready");
        $('#' + clip_id + "_Start").html(start_at);
        $('#' + clip_id + "_End").html(end_at);
        $('#' + clip_id + "_Duration").html(duration);
    });
}

check_file_updates();

function strToDate(timecode){
    var splitTime = timecode.split(/[:.]/);
    var ms;
    if (splitTime[3] !== undefined) {
        ms = parseInt(splitTime[3], 10);
    }
    else{
        ms = 0;
    }
    return new Date(2017, 1, 2, parseInt(splitTime[0], 10), parseInt(splitTime[1], 10), parseInt(splitTime[2], 10), ms);
}


function msToTime(duration) {
    var milliseconds = parseInt((duration%1000)/100)
    , seconds = parseInt((duration/1000)%60)
    , minutes = parseInt((duration/(1000*60))%60)
    , hours = parseInt((duration/(1000*60*60))%24);

    if (milliseconds >= 5){
        seconds++;
    }

    // hours = (hours < 10) ? "0" + hours : hours;
    minutes = (minutes < 10) ? "0" + minutes : minutes;
    seconds = (seconds < 10) ? "0" + seconds : seconds;

    return hours + ":" + minutes + ":" + seconds;
}