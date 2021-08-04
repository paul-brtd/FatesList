// When the user scrolls down 20px from the top of the document, show the button
window.onscroll = function () {
  upbtn = document.querySelector("#up-btn");
  if (document.body.scrollTop > 50 || document.documentElement.scrollTop > 50) {
		upbtn.style.display = "block";
  } 
  else {
		upbtn.style.display = "none";
  }
}

// When the user clicks on the button, scroll to the top of the document
function topFunction() {
  document.body.scrollTop = 0; // For Safari
  document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
}

function modalShow(title, body) {
	document.querySelector("#base-modal-label").innerHTML = title;
	document.querySelector("#base-modal-body").innerHTML = body;
	jQuery("#base-modal").modal();
}

