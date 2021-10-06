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
