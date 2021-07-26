function openf(evt, idp, data, defaultTab) {
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
	if(defaultTab) {
		try {
			history.replaceState(null, "", " ")
		}
		catch {
			window.location.hash = ""
		}
	}
	else {
		window.location.hash = data.id + "-fl";
	}
}

function tabSetup(jq) {
    try {
	jq(document).ready(function(){	
		if(window.location.hash == "") {
			document.querySelector(`#${context.default_tab_button}`).click()
		}
		else {
			try {
				document.querySelector(window.location.hash.replace("-fl", "")).click()
			}
			catch {
				document.querySelector(context.default_tab_button).click()
			}
		}
	});
    }
    catch (err) {
    	alert(err)
    }
}

if(window.$)
	tabSetup($)
else
	tabSetup($j)

