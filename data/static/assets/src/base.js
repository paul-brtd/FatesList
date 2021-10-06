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


function request(data) {
  window.reqData = data
  if(!data.statusCode) {
    data.statusCode = {}
  }

  if(!data.statusCode[429]) {
    data.statusCode[429] = function(d) {
      if(!reqData.rlText) {
        data.rlText = d.responseJSON.reason
      }
      if(!reqData.rlTitle) {
        data.rlTitle = "Ratelimited"
      }
      modalShow(reqData.rlTitle, reqData.rlText)
    }
  }
  if(!data.statusCode[422]) {
    data.statusCode[422] = function(d) {
      json = JSON.stringify(data.responseJSON)
      modalShow("An error occurred during initial proccessing. Try again later", json)
    }
  }
  if(!data.statusCode[404]) {
    data.statusCode[404] = function() {
      modalShow("API is down", "Unfortunately, the Fates List API is down right now. Please try again later")
    }
  }
  if(!data.statusCode[400]) {
    data.statusCode[400] = function(d) {
      if(!reqData.errTitle) {
        reqData.errTitle = "Error"
      }
      modalShow(reqData.errTitle, d.responseJSON.reason)
    }
  }
  if(!data.statusCode[500]) {
    data.statusCode[500] = function() {
      modalShow("Internal Server Error", "We had an error internally on our side when proccessing your request. Please try again later.")
    }
  }

  if(!data.headers) {
    data.headers = {}
  }

  if(data.userAuth) {
    data.headers["Authorization"] = context.user_token
  }
  else if(data.botAuth) {
    data.headers["Authorization"] = context.bot_token
  }

  jQuery.ajax({
    url: data.url,
		method: data.method,
		dataType: "json",
		processData: false,
		contentType: 'application/json',
		data: JSON.stringify(data.json),
		headers: data.headers,
    statusCode: data.statusCode
  })
}