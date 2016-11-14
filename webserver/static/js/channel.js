$(document).ready(function() {
	$('.follow-link').click(function(e) {
		var el = $(e.target);
		var data = {
			member: $(el).data('member'),
			channel: $(el).data('channel')
		}

		$.ajax({
			type: "POST",
			url: "/api/join",
			data: data,
			success: function(res) {
				$(el).html('you belong to #' + data['channel']);
			},
			error: function(er) {
				$(el).html('something broke lol');
				console.error(er);
			}
        });
	});

});