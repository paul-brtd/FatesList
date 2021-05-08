# Vote Webhook

!!! note
    There are many types of webhooks in Fates List. Please choose the one you use carefully. Also note that all Fates List webhooks (excl. Discord Integration) will have a Authorization header with your API Token so you can validate the request.

Vote Webhooks are the webhook type if you want to just capture votes in a simple format that is compatible with other lists. If you want more events like review creation and review voting, edit bot and other such events, you will need to switch to the FatesHook webhook type (see [FatesHook](fateshook.md)) but in most cases, this is not required. It is also harder to handle FatesHook events compared to this and you are better off using websockets (documentation coming soon) if u need those real time stats.

| Key | Description | Type |
| :--- | :--- | :--- |
| id | This is the ID of the user who voted for your bot | [Snowflake](../structures/basic-structures.md#terminology) |
| votes | This is how many votes your bot now has | Integer |
| test | This key is only returned if you are testing your webhook. It will always be true if sent. Use this to check for test webhook or not. | Boolean? |
| mode | This tells you the mode and allows you to quickly check between ”FC” (FatesHook) or ”VOTE” (Vote Webhook). Ignore it if you are not a library | String |
| payload | This will always be ”event” in Vote Webhook. Ignore it. It’s a implementation detail that bots now rely on seeing for some reason. | String |
