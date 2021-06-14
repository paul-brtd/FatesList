# Fates List

Work in progress potential vue/nuxt js frontend rewrite named Lynx for Fates List

Needed APIs:

[] POST /api/auth/login - Login API

[] POST /api/auth/logout - Logout API

[] POST /api/bots/{bot_id}/vote - Vote API

[] DELETE /api/bots/{bot_id} - Delete Bot API

API improvements needed:

Badge data exposed either via a new API or in the Get User API

To think about:

	- Sessions (how will JWT be done securely)
	- Authorization (this will likely be done as we go)
