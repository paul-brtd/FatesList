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
