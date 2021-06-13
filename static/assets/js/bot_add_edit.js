function submitBot(e) {
    try {
    	json = $j('#botform').serializeJSON()
    	tags = document.querySelector("#tags").values
	toReplace = {
	    tags: document.querySelector("#tags").values,
	    extra_owners: json.extra_owners.replace(" ", "").split(","),
            features: document.querySelector("#features").values
        }
	keys = ["extra_owners", "tags", "features"]
	keys.forEach(function (key) {
	    json[key] = toReplace[key].filter(x => x !== "")
	})
	if(context.mode == "edit") {
	    json.bot_id = context.bot_id
	    method = "PATCH"
	}
	else {
	    method = "POST"
	}
	if(json.tags.length == 0 || json.tags[0] == "") {
	    modalShow("Error", "You need to select tags for your bot!")
	    return
	}
	json.owner = context.user_id
	$j.ajax({
		url: `/api/bots/${json.bot_id}`,
		method: method,
		headers: {'Authorization': context.user_token},
		contentType: "application/json",
		data: JSON.stringify(json),
		statusCode: {
			202: function(data) {
				modalShow("Success", "Your bot (and its changes) has been added to the RabbitMQ queue. Your page should auto refresh to it in a few minutes")
				setTimeout(setInterval(function(){
				$j.ajax({
					url: `/api/bots/${json.bot_id}`,
					method: "GET",
					statusCode: {
						200: function(data){
							window.location.replace(`/bot/${json.bot_id}`)
						}
					}
				})
				}, 2000), 1000);
			},
			400: function(data) {
				modalShow("Error", data.responseJSON.reason)
			},
			422: function(data) {
				json = JSON.stringify(data.responseJSON)
				modalShow("An error occurred during initial proccessing. Try again later", json)
			},
			429: function(data) {
				modalShow("Ratelimited", "You are being ratelimited, try again in 5 minutes")
			},
			404: function(data) {
				modalShow("API is down", "Unfortunately, the Fates List API is down right now. Please try again later")
			},
			500: function(data) {
				modalShow("Internal Server Error", "We had an error internally on our side when proccessing your request. Please try again later.")
			}
		}
	})
    }
    catch(err) {
    	alert(err)
    }
};
