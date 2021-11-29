function showToken() {
    but = document.querySelector("#sat")
    usertok = $("#user_tok")
    if(!usertok.html()) {	
        usertok.html(context.user_token)
        but.innerHTML = "Hide"
    }
    else {
        usertok.html("")
        but.innerHTML = "Show"
    }
}		

function pbioEditPane(el, id) {
    bio = document.querySelector('#bio-' + id)
    if(bio.style.display == "none") {
        bio.style.display = 'block';
        document.querySelector("#bio_text-" + id).style.display = "none";
        el.innerHTML = 'Close Edit Menu';
    }
    else {
        bio.style.display = 'none';
        document.querySelector("#bio_text-" + id).style.display = "inline-block";
        el.innerHTML = 'Edit';
    }
}

function toggleJS() {
    request({
        url: `/api/users/${context.user_id}/preferences`,
        userAuth: true,
        method: "PATCH",
        data: {"js_allowed": !context.js_allowed},
        statusCode: {
            200: function(data) {
                window.location.reload()
            }
        }
    })
}

function regenUserToken() {
    request({
        url: `/api/users/${context.user_id}/preferences`,
        userAuth: true,
        method: "PATCH",
	data: {"reset_token": true},
        statusCode: {
            200: function() {
                modalShow("Success!", "Regenerated User Token Successfully!")
                setTimeout(function(){window.location.reload()}, 2000)
            }
        }
    })
}

function updateBio() {
    request({
        url: `/api/users/${context.user_id}/preferences`,
        userAuth: true,
        method: "PATCH",
        data: {"description": document.querySelector("#bio-form-0").value},
        statusCode: {
            200: function() {
                modalShow("Success!", "Changed your bio successfully")
                window.location.reload()
            }
        }
    })
}
