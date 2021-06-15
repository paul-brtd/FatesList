function openf(evt, idp, data) {
	var id = `${idp}-tab`
	// Declare all variables
	var i, tabcontent, tablinks;

	// Get all elements with class="tabcontent" and hide them
	tabcontent = document.getElementsByClassName("tabcontent");
	for (i = 0; i < tabcontent.length; i++) {
		tabcontent[i].style.display = "none";
	}

	// Get all elements with class="tablinks" and remove the class "active"
	tablinks = document.getElementsByClassName("tablinks");
	for (i = 0; i < tablinks.length; i++) {
		tablinks[i].className = tablinks[i].className.replace(" active", "");
	}

	// Show the current tab, and add an "active" class to the button that opened the tab
	document.getElementById(id).style.display = "block";
	evt.currentTarget.className += " active";
	if(data.id != "bot-long-desc-tab-button")
		window.location.hash = data.id + "-fl";
	else 
		window.location.hash = ""
}

var rating = 0;
var slider = document.querySelectorAll(".range-slider");
// Update the current slider value (each time you drag the slider handle)
for(var i = 0; i < slider.length; i++) {
	output_id = slider[i].getAttribute("output")
	document.getElementById(output_id).innerHTML = "Drag the slider to change your rating"; // Display the default slider value
	slider[i].oninput = function() {
		output = document.getElementById(this.getAttribute("output"))
		console.log(output)
		state = parseState(this.value)
		output.innerHTML = state + ", " + this.value;
	}
}

function parseState(v) {
	state = ""
	if(v < 1)
		state = "Atrocity"
	else if(v < 2)
		state = "Absymal"
	else if(v < 3)
		state = "Really Poor"
	else if(v < 4)
		state = "Poor"
	else if(v < 5)
		state = "Below Average"
	else if(v < 6)
		state = "Average"
	else if(v < 7)
		state = "Above Average"
	else if(v < 8)
		state = "Meets Expectations"
	else if(v < 9)
		state = "Great"
	else if(v < 10)
		state = "Exceeds Expectations"
	else if(v == 10)
		state = "Without a doubt, perfect"
	return state
}

try {
	$(document).ready(function(){	
		if(window.location.hash == "")
			document.querySelector('#long-desc-tab-button').click()
		else {
			try {
				document.querySelector(window.location.hash.replace("-fl", "")).click()
			}
			catch {
				document.querySelector('#long-desc-tab-button').click()
			}
		}
	});
}
catch (err) {}
function onSubmit(token) {
	document.getElementById("vote").submit();
}

		var ds = 0; // Whether the user is doing something
		function botReviewEditPane(el, id) {
			rev = document.querySelector('#review-' + id)
			if(rev.style.display == "none" && ds == 0) {
				rev.style.display = 'block';
				el.innerHTML = 'Close';
				ds = 1;
				return
			}
			else if(ds == 1) {
				rev.style.display = 'none';
				el.innerHTML = 'Edit';
				ds = 0;
			}
		}
function replyReview(el, id) {
	rev = document.querySelector('#reviewreply-' + id)
	if(rev.style.display == "none" && ds == 0) {
		rev.style.display = 'block';
		el.innerHTML = 'Close';
		ds = 2;
		return;
	}
	else if(ds == 2) {
		rev.style.display = 'none';
		el.innerHTML = 'Reply';
		ds = 0;
	}
}

$( document ).ready(function() {
	setTimeout(function() {document.querySelector("#rating-desc-avg").innerHTML = parseState(context.reviews.average_rating) + ", " + context.reviews.average_rating}, 300); 
});

function voteBot() {
	if(!context.logged_in)
		window.location.replace(`/auth/login?redirect=/${context.type}/${context.id}/vote&pretty=to vote for this bot`)
	$.ajax({
		url: `/api/${context.type}s/${context.id}/votes`,
		method: "PATCH",
		headers: {"Authorization": context.user_token},
		contentType: "application/json",
		data: JSON.stringify({"user_id": context.user_id}),
		statusCode: {
			200: function(data) {
				modalShow("Voted!", "You have successfully voted for this bot")
				setTimeout(() => window.location.reload(), 1500)
			},
			400: function(data) {
				modalShow(data.responseJSON.reason, `Please wait ${data.responseJSON.human} before trying to vote for this bot`)
			},
			429: function(data) {
				modalShow("Rate Limited", "You are being ratelimited. Please try voting again in a few minutes")
			}
		}
	})
}

function commandModal(name) {
	cmd = document.querySelector("#cmd-" + name.replace(" ", "")).textContent
	cmd = JSON.parse(cmd)
	args = cmd.args.toString().replace(",", " ")
	modalShow(`More information (${cmd.friendly_name})`, `
		Command Name: ${cmd.cmd_name}<br>
		Arguments: ${args.replace(">", "</span>").replace("<", "<span class='arg'>")}<br>
		ID: ${cmd.id}
	`) 
}

function getCommands(bot_id) {
	commandsTab = document.querySelector("#commands-tab")
	error = document.querySelector("#commands-error")
	$.get({
		url: `/api/bots/${context.id}/commands?lang=${context.site_lang}`,
		statusCode: {
			404: function(data) {
				error.textContent = "No Commands Found"
			},
			200: function(data_u) {
				sortjson = () => {data = Object.keys(data_u).sort().reduce(
					  (obj, key) => { 
						obj[key] = data_u[key]; 
						return obj;
					  }, 
					{}
				);
					return data
				}
				data = sortjson(data_u);
				commands = `<p style='font-size: 30px'>Commands List</p><p>Click on a category to expand/collapse it</p>`
				$.each(data, function(group, gdata) {
					if(group == "default")
						group = "Miscellaneous" 
					commands += `
					<a class="white" style="font-size: 25px" aria-expanded="true" data-toggle="collapse" href="#${group}table">${group}</a>
					<div class="collapse show" id='${group}table'>
					<table style="margin: 0 auto !important;">
					<colgroup>
						<tr>
							<th style="border-right: none;">Name</th>
							<th style="border-right: none;">Description</th>
							<th style="border-right: none;">Docs</th>
							<th style="border-right: none;">Premium</th>
							<th style="border-right: none;">More</th>
						</tr>
					</colgroup>
				`
				/* TODO: Fill in HTML */
					gdata.forEach(function(cmd, i, a) {
							if(cmd.args.length == 0)
								cmd.args = ["No arguments"]
							if(cmd.doc_link.replace(" ", "") == "")
								docs = "No docs available"
							else
								docs = `<a class='long-desc-link' href='${cmd.doc_link}'>Docs</a>`
							commands += `
							<colgroup>
								<tr>
									<span style="display: none" id="cmd-${cmd.name}">${JSON.stringify(cmd)}</span>
									<td>${cmd.friendly_name}</td>
									<td>${cmd.description}</td>
									<td>${docs}</td>
									<td>${cmd.premium_only.toString().replace("true", "Yes").replace("false", "No")}</td>
									<td><a class='long-desc-link' href='javascript:void' onclick="commandModal('${cmd.name}')">View</a>
							</tr>
						</colgroup>
						`
						});
					commands += `</table></div>`
				});
				commandsTab.innerHTML = commands
			}
		}
	})
}

setTimeout(function(){getCommands(context.id)}, 700)

function deleteReview(rev_id) {
	$.ajax({
		type: 'DELETE',
		url: `/api/${context.type}s/${context.id}/reviews/${rev_id}`,
		data: JSON.stringify({"user_id": context.user_id}),
		headers: {"Authorization": context.user_token},
		processData: false,
		contentType: 'application/json',
		statusCode: {
			400: function(data) {alert(data.error)}
		}	
	});
	modalShow("Success!", "Deleted Review Successfully")
}

function upvoteReview(rev_id) {
	$.ajax({
		type: 'PATCH',
		url: `/api/${context.type}s/${context.id}/reviews/${rev_id}/votes`,
		data: JSON.stringify({"upvote": true, "user_id": context.user_id}),
		headers: {"Authorization": context.user_token},
		processData: false,
		contentType: 'application/json',
		statusCode: {
			400: function(data) {
				modalShow("Already Upvoted", "You have already upvoted this review. You cannot upvote it again");
			},
			200: function(data) {
				modalShow("Success!", "Successfully upvoted this review")
				setTimeout(() => window.location.reload(), 1500)
			},
			404: function(data) {
				modalShow("404 Not Found", "Review does not exist on our database! Maybe it has been deleted?")
			},
			401: function(data) {
				modalShow("Unauthorized", "We could not authenticate you, make sure you are logged in")
			}
		}
	});

}

function downvoteReview(rev_id) {
	$.ajax({
		type: 'PATCH',
		url: `/api/${context.type}s/${context.id}/reviews/${rev_id}/votes`,
		data: JSON.stringify({"upvote": false, "user_id": context.user_id}),
		headers: {"Authorization": context.user_token},
		processData: false,
		contentType: 'application/json',
		statusCode: {
			400: function(data) {
				modalShow("Already Downvoted", "You have already downvoted this review. You cannot downvote it again");
			},
			200: function(data) {
				modalShow("Success!", "Successfully downvoted this review")
				setTimeout(() => window.location.reload(), 1500)
			},
			404: function(data) {
				alert("Review does not exist or this feature isn't done yet!")
			},
			401: function(data) {
				alert("We could not authenticate you, make sure you are logged in")
			}
		}
	});

}
