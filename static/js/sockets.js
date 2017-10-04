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
        console.log("length", ready_clips)
        for (var j = 0; j < ready_clips.length; j++) {
            console.log('started')
            var clip_id = ready_clips[j][0];
            var start_at = ready_clips[j][1];
            var end_at = ready_clips[j][2];
            console.log(clip_id + " : " + start_at  + " : " + end_at);
            var statusSpan = clip_id + "_Status";
            $('#'+statusSpan).html("Ready");
            var clipIndex = clips_to_update.clips.indexOf(clip_id);
            //remove it from the list of clips to check
            if (clipIndex > -1){
                clips_to_update.clips.splice(clipIndex, 1);
            }
        }
        if (clips_to_update.clips.length == 0){
            //socket.off();
            console.log("all available clips are updated");
        }
    });

    // socket.on('new casemessage', function(results){
    //     console.log(results);
    //     showNewMessage(results);
    // });

    // socket.on('remove casemessage', function(results){
    //     console.log(results);
    //     $('#div_'+results).remove()
    // });
}

check_file_updates();