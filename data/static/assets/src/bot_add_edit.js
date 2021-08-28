// replaceAll polyfill
if (!String.prototype.replaceAll) {
	String.prototype.replaceAll = function(str, newStr){
		if (Object.prototype.toString.call(str).toLowerCase() === '[object regexp]') {
			return this.replace(str, newStr);
		}

		return this.replace(new RegExp(str, 'g'), newStr);
	};
}


function submitBot() {
    context.error = null
    modalShow("Saving", "Please wait for a few moments while we save your bot")
    try {
	json = {}
	context.form_values.text.forEach(function (key) {
	    el = document.querySelector(`#${key}`)
	    json[key] = el.value
	    if(el.getAttribute("required") != null && !el.value){
		modalShow("Error", `You must enter a ${key.replaceAll("_", " ")} for your bot!`)
		context.error = key
		return
	    }
	})
	if(context.error) {
		return
	}
	context.form_values.select_single.forEach(function (key) {
	    json[key] = document.querySelector(`#${key}`).value
	})

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
	    method = "PUT"
	}
	context.form_values.select_multiple.forEach(function (key) {
		json[key] = document.querySelector(`#${key}`).values
	})
	if(json.tags.length == 0 || json.tags[0] == "") {
	    modalShow("Error", "You need to select tags for your bot!")
	    return
	}
	jQuery.ajax({
		url: `/api/users/${context.user_id}/bots/${json.bot_id}`,
		method: method,
		headers: {'Authorization': context.user_token},
		contentType: "application/json",
		data: JSON.stringify(json),
		statusCode: {
			202: function(data) {
				modalShow("Success", "Your bot (and its changes) has been added to the RabbitMQ queue. Your page should auto refresh to it in a few minutes")
				setTimeout(setInterval(function(){
				jQuery.ajax({
					url: `/api/bots/${json.bot_id}`,
					method: "HEAD",
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
				modalShow("Ratelimited", data.responseJSON.detail)
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

function deleteBot() {
	bot_id_prompt = prompt("In order to confirm your request, please enter the Bot ID for your bot", "")
	if(!bot_id_prompt || bot_id_prompt != context.bot_id) {
             	// User did not type proper bot id
		modalShow("Failed to delete bot", "This bot couldn't be deleted as you did not confirm that you wanted to do this!")
		return
	}
	modalShow("Deleting Bot..", "Please wait...")
	jQuery.ajax({
		url: `/api/users/${context.user_id}/bots/${context.bot_id}`,
		method: "DELETE",
		headers: {'Authorization': context.user_token},
		contentType: "application/json",
		statusCode: {
			202: function(data) {
				modalShow("Bot Deleted :(", "This bot has been added to our queue of bots to delete and will be deleted in just a second or two")
				setTimeout(setInterval(function(){
				jQuery.ajax({
					url: `/api/bots/${context.bot_id}`,
					method: "GET",
					statusCode: {
						404: function(data){
							window.location.replace(`/`)
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
				modalShow("Ratelimited", data.responseJSON.detail)
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

function previewLongDesc(){
	html = document.querySelector("#long_description_type").value;
	ld = document.querySelector("#long_description").value;
	if(context.mode == "edit") {
		headers = {"Authorization": context.bot_token}
	}
	else {
		headers = {}
	}
	if(ld == "") {
		return
	}
        jQuery.ajax({
           type: 'POST',
           dataType: 'json',
	   headers: headers,
	   contentType: "application/json",
	   url: `/api/preview?lang=${context.site_lang}`,
           data: JSON.stringify({"html_long_description": html, "data": ld}),
	   statusCode: {
           "200": function(data) {
               jQuery("#ld-preview").html(data.html)
           },
           "429": function(data) {
		modalShow("Rate Limited", data.responseJSON.detail)
           },
	   "422": function(data) {
	   	modalShow("Error", JSON.stringify(data))
	   }
	}
    });

}
function showToken(but) {
	
	token = document.querySelector("#api-token")
	if(!token.getAttribute("show")) {
		token.innerHTML = context.bot_token
		but.innerHTML = "Hide"
		token.setAttribute("show", "true")
	}
	else {
                token.innerHTML = "Click 'Show' to see your bots token";
		but.innerHTML = "Show"
		token.removeAttribute('show')
	}
  }
  function postStats() {
	server_count = document.querySelector("#server-count").value
  	payload = {"guild_count": server_count}
	jQuery.ajax({
		headers: {'Authorization': context.bot_token},
		method: 'POST',
		url: `/api/bots/${context.bot_id}/stats`,
		contentType: 'application/json',
		data: JSON.stringify(payload),
	});
	modalShow("Success", "Done posting stats. You may leave this page or continue editing this bot!")
  }
  function regenToken() {
	jQuery.ajax({
	   headers: {'Authorization': context.bot_token},
	   type: 'PATCH',
	   url: `/api/bots/${context.bot_id}/token`,
	   processData: false,
	   contentType: 'application/json',
	});
	alert("Regenerated Token Successfully")
	window.location.reload()
  }

function testHook(url, type) {
	headers = {"Authorization": context.bot_token}
	jQuery.ajax({
		url: `/api/bots/${context.bot_id}/testhook`,
		dataType: "json",
		headers: headers,
		type: "POST",
		processData: false,
		contentType: 'application/json',
		statusCode: {
			200: function(data) {
				modalShow("Sent test query", "See the below tip if you didn't get it!")
			}
		}
	})
  }

function hideSaveOnAboutTab(id, evt, data) {
	if(id == "about" || id == "actions") {
		document.querySelector("#save-changes").style.display = "none"
	}
	else {
		document.querySelector("#save-changes").style.display = "initial"
	}
}


function submitAppeal() {
	modalShow("Sending appeal...", "Please wait while Fates List sends your appeal real quick!")
	appeal = document.querySelector("#appeal").value
	if(appeal.length < 7) {
		modalShow("Error", "Your appeal must be at least 7 characters long")
		return
	}
	headers = {"Authorization": context.bot_token}
	json = JSON.stringify({"appeal": appeal})
	jQuery.ajax({
		url: `/api/v2/bots/${context.bot_id}/appeal`,
		method: "POST",
		dataType: "json",
		processData: false,
		contentType: 'application/json',
		data: json,
		headers: headers,
		statusCode: {
			200: function() {
				modalShow("Success", "Done posting appeal. Please wait while our staff reviews it!")
				setTimeout(function(){window.location.replace(`/bot/${context.bot_id}`)}, 3000)
			},
			400: function(data) {
				modalShow("Error", data.responseJSON.reason)
			},
			404: function(data) {
				modalShow("Error", "This bot could not be found. Has it been deleted?")
			},
		}
	})
}

function autofillBot() {
	function qs(q) {
		return document.querySelector(q)
	}
	bot_id = qs("#bot_id").value
	if(!bot_id) {
		return
	}
	jQuery.ajax({
		method: "GET",
		url: `https://discord.com/api/v9/applications/${bot_id}/rpc`,
		statusCode: {
			200: function(data) {
				if(!data.bot_public) {
					modalShow("Cannot autofill", "This bot is not a public bot")
					return
				}
				if(data.description) qs("#description").value = data.description
				if(data.summary) qs("#long_description").textContent = data.summary
				if(data.privacy_policy_url) qs("#privacy_policy").value = data.privacy_policy_url
				if(data.slug) qs("#vanity").value = data.slug.toLowerCase()
				else qs("#vanity").value = data.name.replaceAll(" ", "").toLowerCase()
				modalShow("Autofill Done", "We've autofilled as much of what we could find on your bots application!")
			},
			404: function(data) {
				modalShow("This bot does not exist!", "Please check the bot id you inputted")
			}

		}
	})

}
