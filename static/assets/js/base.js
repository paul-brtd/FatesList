var rating = 0;
var slider = document.querySelectorAll(".bot-range-slider");
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
$( document ).ready(function() {
	setTimeout(function() {document.querySelector("#rating-desc-avg").innerHTML = parseState(8.97) + ", " + 8.97}, 300); 
});

function openf(evt, id, data) {
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

function deleteReview(rev_id) {
	$.ajax({
		type: 'DELETE',
		url: `/api/bots/519850436899897346/reviews/${rev_id}`,
		data: JSON.stringify({"user_id": "563808552288780322"}),
		headers: {"Authorization": "Rt1PWnbFefvj5OFPq8cQtEZBnu4IOICLzxNFv3DRnBZDhkV80JMMTPofMT3sTjAjni0cMDCfzEUBvxvBwhmfTDzRpUXbKCh2w8b0W"},
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
		url: `/api/bots/519850436899897346/reviews/${rev_id}/votes`,
		data: JSON.stringify({"upvote": true, "user_id": "563808552288780322"}),
		headers: {"Authorization": "Rt1PWnbFefvj5OFPq8cQtEZBnu4IOICLzxNFv3DRnBZDhkV80JMMTPofMT3sTjAjni0cMDCfzEUBvxvBwhmfTDzRpUXbKCh2w8b0W"},
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
		url: `/api/bots/519850436899897346/reviews/${rev_id}/votes`,
		data: JSON.stringify({"upvote": false, "user_id": "563808552288780322"}),
		headers: {"Authorization": "Rt1PWnbFefvj5OFPq8cQtEZBnu4IOICLzxNFv3DRnBZDhkV80JMMTPofMT3sTjAjni0cMDCfzEUBvxvBwhmfTDzRpUXbKCh2w8b0W"},
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

	$(document).ready(function(){	
		if(window.location.hash == "")
			document.querySelector('#bot-long-desc-tab-button').click()
		else {
			try {
				document.querySelector(window.location.hash.replace("-fl", "")).click()
			}
			catch {
				document.querySelector('#bot-long-desc-tab-button').click()
			}
		}
	});
function onSubmit(token) {
	document.getElementById("vote").submit();
}
