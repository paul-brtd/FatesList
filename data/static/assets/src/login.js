function getLoginLink() {
	modalShow("Logging you in...", "Please wait...")
	scopes = ["identify"]
	scopes_total = {
		"server_list": "guilds",
		"join_servers": "guilds.join"
	}
	$.each(scopes_total, function(k, v){
		selected = document.querySelector(`#${k}`).checked
		if(selected) {
			scopes.push(v)
		}
	})
	localStorage.setItem("login-scopes", JSON.stringify(scopes))
	data = {
		"redirect": context.redirect,
		"scopes": scopes
	}
	$.ajax({
		method: "POST",
		url: "/api/v2/oauth",
		dataType: "json",
		processData: false,
		contentType: 'application/json',
		data: JSON.stringify(data),
		statusCode: {
			206: function(data) {
				window.location.href = data.url	
			},
			400: function(data) {
				modalShow("Error", data.responseJSON.reason)
			}
		}

	})
}
