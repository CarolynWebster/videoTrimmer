$(document).ready(function() {

	$('form').on('submit', function(event) {

		event.preventDefault();

		var formData = new FormData($('#vid-upload')[0]);
		formData.append('media', $('#media')[0].files[0]);
		formData.append('tscript', $('#tscript')[0].files[0]);
		formData.append('name', $('#name').val());
		formData.append('date', $('#date-taken').val());
		formData.append('case_id', $('#case_id').val());


		$.ajax({
			xhr : function() {
				var xhr = new window.XMLHttpRequest();

				xhr.upload.addEventListener('progress', function(e) {

					if (e.lengthComputable) {

						console.log('Bytes Loaded: ' + e.loaded);
						console.log('Total Size: ' + e.total);
						console.log('Percentage Uploaded: ' + (e.loaded / e.total));

						var percent = Math.round((e.loaded / e.total) * 100);

						$('#progressBar').attr('aria-valuenow', percent).css('width', percent + '%').text(percent + '%');

					}

				});

				return xhr;
			},
			type : 'POST',
			url : '/upload-video',
			data : formData,
			processData : false,
			contentType : false,
			success : function(case_id) {
				window.location='/cases/'+case_id;
			}
		});

	});

});