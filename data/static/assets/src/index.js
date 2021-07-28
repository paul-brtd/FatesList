		function randomBotRoll() {
			$.ajax({
				url: "/api/bots/0/random?lang={{context.site_lang}}",
				method: "GET",
				statusCode: {
					429: function(data) {
						modalShow("You are rolling too fast!", data.responseJSON.detail)
					},
					422: function(data) {
						modalShow("Something went wrong", "Please report this on our support server")
					},
					200: function(data) {
						random_bots = document.querySelector("#random-bots")
		
						// Get banner
						if (!data.banner_card) {
							banner = "/static/assets/prod/banner.webp"
						}
						else {
							banner = data.banner_card
						}
						if (data.state == 6) { // State 6 is certified
							certified_ico = "visible"
						}
						else {
							certified_ico = "hidden"
						}
						banner_dom = random_bots.querySelectorAll(".bot-card-banner")[0] // Banner
						banner_dom.setAttribute("data-background-image", banner)
						random_bots.querySelectorAll(".bot-card-cert")[0].style.visibility = certified_ico // Certified
						avatar_dom = random_bots.querySelectorAll(".bot-card-avatar")[0] // Avatar
						avatar_dom.setAttribute("data-src", data.avatar)
						avatar_dom.setAttribute("data-loaded", "false") // Lozad Reload Avatar
						banner_dom.setAttribute("data-loaded", "false") // Lozad Reload Banner
						observer.observe() // Lozad Reobserve
						view_links = random_bots.querySelectorAll(".bot-card-view-link")
						for (let i = 0; i < view_links.length; i++) {
							view_links[i].setAttribute("href", "/bot/" + data.bot_id.toString())
						}
						username_dom = random_bots.querySelectorAll(".bot-card-username-txt")[0].innerHTML = data.username
						random_bots.querySelectorAll(".bot-card-description-txt")[0].innerHTML = data.description
						random_bots.querySelectorAll(".bot-servers")[0].innerHTML = data.formatted.guild_count
						random_bots.querySelectorAll(".bot-votes")[0].innerHTML = data.formatted.votes
						random_bots.querySelectorAll(".bot-card-invite-link")[0].setAttribute("href", "/bot/" + data.bot_id.toString() + "/invite")
					}
				}
			})
		}
		window.addEventListener("load", randomBotRoll)
