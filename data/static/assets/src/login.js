function getLoginLink() {
	modalShow("Logging you in...", "Please wait...")
	scopes = ["identify"]
	scopes_total = {
		"join_servers": "guilds.join"
	}
	$.each(scopes_total, function(k, v){
		selected = document.querySelector(`#${k}`).checked
		if(selected) {
			scopes.push(v)
		}
	})

	if(!context.redirect) {
		context.redirect = localStorage.getItem("current-page")
		if(!context.redirect) {
			context.redirect = "/"
		}
	}

	localStorage.setItem("login-redirect", context.redirect)
	localStorage.setItem("login-scopes", JSON.stringify(scopes))
	data = {
		"redirect": context.redirect,
		"scopes": scopes
	}
	request({
		method: "POST",
		url: "/api/v2/oauth",
		json: data,
		statusCode: {
			206: function(data) {
				window.location.href = data.url	
			},
		}
	})
}
