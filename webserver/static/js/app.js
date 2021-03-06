$(document).ready(function() {

	var filled_heart = '<span class="heart" data-pid="{{post.pid}}""><svg class="svg-icon" width="57" height="25"><path d="M12.5 21a.492.492 0 0 1-.327-.122c-.278-.24-.61-.517-.978-.826-2.99-2.5-7.995-6.684-7.995-10.565C3.2 6.462 5.578 4 8.5 4c1.55 0 3 .695 4 1.89a5.21 5.21 0 0 1 4-1.89c2.923 0 5.3 2.462 5.3 5.487 0 3.97-4.923 8.035-7.865 10.464-.42.35-.798.66-1.108.93a.503.503 0 0 1-.327.12z" fill-rule="evenodd"></path></svg></span>';
	var empty_heart = '<span class="heart" data-pid="{{post.pid}}"><svg class="svg-icon" width="57" height="25"><path d="M12.5 21a.492.492 0 0 1-.327-.122c-.278-.24-.61-.517-.978-.826-2.99-2.5-7.995-6.684-7.995-10.565C3.2 6.462 5.578 4 8.5 4c1.55 0 3 .695 4 1.89a5.21 5.21 0 0 1 4-1.89c2.923 0 5.3 2.462 5.3 5.487 0 3.97-4.923 8.035-7.865 10.464-.42.35-.798.66-1.108.93a.503.503 0 0 1-.327.12zM8.428 4.866c-2.414 0-4.378 2.05-4.378 4.568 0 3.475 5.057 7.704 7.774 9.975.243.2.47.39.676.56.245-.21.52-.43.813-.68 2.856-2.36 7.637-6.31 7.637-9.87 0-2.52-1.964-4.57-4.377-4.57-1.466 0-2.828.76-3.644 2.04-.1.14-.26.23-.43.23-.18 0-.34-.09-.43-.24-.82-1.27-2.18-2.03-3.65-2.03z" fill-rule="evenodd"></path></svg></span>';


	if (window.location.pathname != "/notifications"){	
		$('.post').each(function(idx, el) {
			var heart = $(el).find('.heart');

			var data = {
				pid: $(el).data('pid'),
				user: window.currentUser
			}

			var liked = false;
			var numLikes = $(el).data('likes');

			$.ajax({
				type: "POST",
				url: "/api/like_query",
				data: data,
				success: function(res) {
					liked = res['liked'];
					$(el).data('liked', liked);
					if (liked){
						$(heart).first().html(filled_heart);
					}
				},
				error: function(er) {
					console.error(er);
				}
	        });

	        function clickHeart(post) {
	        	var h = $(post).find('.heart');
				var numLikesEl = $(post).find('.num-likes');
				var numLikes = $(post).data('likes');
				var liked = $(post).data('liked');

				var data = {
					pid: $(post).data('pid'),
					user: window.currentUser
				}

				if (!(window.currentUser)) {
					$(numLikesEl).html('sign up');
					return;
				}

				if (!liked) {
					$(heart).first().html(filled_heart);
					$(post).data('liked', true);
					$(numLikesEl).html(numLikes + 1);
					$(post).data('likes', numLikes + 1);
					$.ajax({
						type: "POST",
						url: "/api/like",
						data: data,
						error: function(er) {
							console.error(er);
						}
			        });
				}
				else {
					$(heart).first().html(empty_heart);
					$(post).data('liked', false);
					$(numLikesEl).html(numLikes - 1);
					$(post).data('likes', numLikes - 1);
					$.ajax({
						type: "POST",
						url: "/api/unlike",
						data: data,
						error: function(er) {
							console.error(er);
						}
			        });
				}
	        }

	        $(heart).click(function(e) {
	        	clickHeart(el);
	        });
		});
	}
});