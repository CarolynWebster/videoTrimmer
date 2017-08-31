function check_file_updates() {    
    processing_clips = $('.clip-processing');
    console.log(processing_clips);
    clips_to_update = new Object();
    clips_to_update.clips = [];
    for (var i = 0; i < processing_clips.length; i++){
        var clip_id = processing_clips[i].id;
        clip_id = clip_id.replace("_Status", "");
        clips_to_update.clips.push(parseInt(clip_id));
    }
    var to_send = JSON.stringify(clips_to_update);

    var socket = io.connect('http://' + document.domain + ':' + location.port);
    socket.on('connect', function() {
        socket.emit('update_clips', to_send);
    });
    socket.on('server update', function(results){
        var ready_clips = results['clips'];
        console.log(ready_clips);
        for (var j = 0; j < ready_clips.length; j++) {
            var statusSpan = ready_clips[j] + "_Status";
            $('#'+statusSpan).html("Ready");
            var clipIndex = clips_to_update.clips.indexOf(ready_clips[j]);
            //remove it from the list of clips to check
            if (clipIndex > -1){
                clips_to_update.clips.splice(clipIndex, 1);
            }
        }
        if (clips_to_update.clips.length == 0){
            socket.off();
            console.log("socket off");
        }
    })
}

check_file_updates();