function voteBot() {
	if(context.type == "server") {
		modalShow("Voting for servers", "Do /vote in this server to cote for it and get exclusive perks if the server supports vote rewards")
		return
	}
	if(!context.logged_in) {
		window.location.href = `/fates/login?redirect=/${context.type}/${context.id}/vote&pretty=to vote for this bot`
		return
	}
	modalShow("Voting...", "Please wait...")
	request({
		url: `/api/users/${context.user_id}/${context.type}s/${context.id}/votes`,
		method: "PATCH",
		userAuth: true,
		statusCode: {
			200: function(data) {
				modalShow("Voted!", "You have successfully voted for this bot")
				setTimeout(() => (window.location.href = `/${context.type}/${context.id}`), 1500)
			},
			400: function(data) {
				modalShow(data.responseJSON.reason, `Please wait ${data.responseJSON.wait_time.hours} hours, ${data.responseJSON.wait_time.minutes} minutes and ${data.responseJSON.wait_time.seconds} seconds before trying to vote for this bot`)
			}
		}
	})
}
