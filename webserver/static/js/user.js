$(document).ready(function() {
	$('.follow-link').click(function(e) {
		var el = $(e.target);
		var data = {
			follower: $(el).data('follower'),
			followee: $(el).data('followee')
		}

		$.ajax({
			type: "POST",
			url: "/api/follow",
			data: data,
			success: function(res) {
				$(el).html('you follow @' + data['followee']);
			},
			error: function(er) {
				$(el).html('something broke lol');
				console.error(er);
			}
        });
	});

});