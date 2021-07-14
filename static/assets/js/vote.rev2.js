function voteBot() {
	if(!context.logged_in)
		window.location.replace(`/auth/login?redirect=/${context.type}/${context.id}/vote&pretty=to vote for this bot`)
	modalShow("Voting...", "Please wait...")
	$.ajax({
		url: `/api/users/${context.user_id}/${context.type}s/${context.id}/votes`,
		method: "PATCH",
		headers: {"Authorization": context.user_token},
		contentType: "application/json",
		statusCode: {
			200: function(data) {
				modalShow("Voted!", "You have successfully voted for this bot")
				setTimeout(() => window.location.reload(), 1500)
			},
			400: function(data) {
				modalShow(data.responseJSON.reason, `Please wait ${data.responseJSON.wait_time.hours} hours, ${data.responseJSON.wait_time.minutes} minutes and ${data.responseJSON.wait_time.seconds} seconds before trying to vote for this bot`)
			},
			429: function(data) {
				modalShow("Rate Limited", "You are being ratelimited. Please try voting again in a few minutes")
			}
		}
	})
}
