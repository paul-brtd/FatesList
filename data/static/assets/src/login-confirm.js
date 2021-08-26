		function makeSmaller() {
			$('#msg').contents().unwrap().wrap("<h5 id='msg' class='text-center' style='color: red'></h5>");
		}
		function loginUser() {
			retry = "<br/><br/><a href='https://fateslist.xyz/fates/login'>Try Again?</a>"
			searchParams = new URLSearchParams(window.location.search)
			code = searchParams.get("code")
			state = searchParams.get("state")
			if(!code || !state) {
				makeSmaller()
				$("#msg").html("Invalid code/state" + retry)
				return
			}
			$.ajax({
				url: "/api/users",
				method: "POST",
				contentType: "application/json",
				data: JSON.stringify({"code": code, "state": state}),
				statusCode: {
					206: function(data) {
						window.location.href = localStorage.getItem("login-redirect")
					},
					400: function(data) {
						makeSmaller()
						$("#msg").html(data.responseJSON.reason + retry)
					},
					403: function(data) {
						makeSmaller()
						banInfo = `
	      					<br/><br/>
						<p style="text-align: left !important; margin-left: 10em">
						You have been ${data.responseJSON.ban.type} banned.<br/>
						As a result, ${data.responseJSON.ban.desc}
	       					<br/><br/>
						<strong>Please contact a Fates List Staff Member to appeal this ban</strong>
						</p>
						`
						$("#msg").html(data.responseJSON.reason + banInfo)
					},
					422: function(data) {
						makeSmaller()
						$("#msg").html("Invalid request" + retry)
					},
					429: function(data) {
						makeSmaller()
						$("#msg").html(data.responseJSON.reason + retry)
					},
					500: function(data) {
						makeSmaller()
						$("msg").html("Internal Server Error" + retry)
					}
				}
			})
		}
	$(document).ready(
		function() {
			loginUser()
		}
	)


