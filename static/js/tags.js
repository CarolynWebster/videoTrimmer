//download all clips from a case based on tag
function handleTaggedClips(evt){
    var clips_to_get = evt.currentTarget.value;
    var callFunction = evt.currentTarget.id;

    // get the current time for the zip
    var currTime = getCurrentTime();
    
    var formInputs = {
        'case_id': currCaseID,
        'clips': String(clips_to_get),
        'call_func': callFunction,
        'vid_type': 'clip',
        'curr_time': currTime
    };

    $.post('/handle-clips', formInputs, function() {
        console.log('request complete');
    });
}

$(".tag-download").on('click', handleTaggedClips);

function updateTags (){
    var new_tags = $('#new_tags_input').val();
    var formInputs = {
        'new_tags': new_tags,
        'case_id': currCaseID,
    };
    $.post('/add-tags', formInputs, function () {
        //refresh the page after adding users
        location.reload();
    });
}
$('#add_tags').on('click', updateTags);

function deleteTag (evt){
    var confirm_delete = confirm("Are you sure you want to remove this tag? This action cannot be undone and will remove all associations with this tag.");

    if (confirm_delete === true){
        var tag = evt.currentTarget.id;
        var formInputs = {
            'del_tag': tag,
            'case_id': currCaseID
        };
        $.post('/delete-tag', formInputs, function(results) {
            //get id for tr holding that user
            var tag_row = "#Tag_" + tag;
            $(tag_row).remove();
            console.log(results);
        });
    }

}
$('.remove-tag-x').on('click', deleteTag);


// Video clip tag functions
function removeTag(evt){
  //confirm they want to delete that tag
  var youreSure = confirm('Are you sure you want to delete this tag?');
  
  //if they say yes
  if (youreSure){
    //get the tag name and clipid from the button id
    var clipIdTarget = evt.currentTarget.id;
    var tagInfo = clipIdTarget.split('_');
    var tagId = tagInfo[0];
    var clipId = tagInfo[1];

    tagInputs = {
      'clip_id': clipId,
      'tag_id': tagId
    };

    $.post('/remove-cliptag', tagInputs, function(results) {
      console.log(results, clipIdTarget);
        //delete the appropriate tag btn
        var tagClipId = results.tag_id+"_"+results.clip_id;
        $('#'+tagClipId).remove();
    });
  }
}

function addTags(evt){
    var clipIdTarget = evt.currentTarget.id;
    var selTarget = '#sel_' + clipIdTarget;
    var tdTarget = '#tagtd_' + clipIdTarget;
    tagInputs = {
        'clip_id': clipIdTarget,
        'tag_id': $(selTarget).val()
    };
    $.post('/add-cliptags', tagInputs, function (results) {
        console.log(results);
        // returns dict with {tag_id, clip_id, tag_name}
        var tagClipId = results.tag_id+"_"+results.clip_id;
        var tagBtn = "<button class='tag-btn' value='"+tagClipId+"' id='"+tagClipId+"'>"+results.tag_name+"<i class='glyphicon glyphicon-remove'></i></button>";
        $(tdTarget).append(tagBtn);
        //add event listener to new btn
        $('#'+tagClipId).on('click', removeTag);
    });
}

$(".casetag").on('click', addTags);
$(".tag-btn").on('click', removeTag);
