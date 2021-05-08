# FatesHook (Fates Client)

!!! note
    There are many types of webhooks in Fates List. Please choose the one you use carefully. Also note that all Fates List webhooks (excl. Discord Integration) will have a Authorization header with your API Token so you can validate the request.

FatesHook is a webhook type to get additional events like edit bot, review events and more. These events cannot be sent using something like vote webhook and need their own format which is what FatesHook is for. All Fates Client Webhooks like the Vote Webhook will be sent as a JSON with the Authorization header being your API token.

!!! warning
    All Fates Client libraries which support v2 will support this. Some v1 libraries may also work but this is not guaranteed as the format for webhooks has changed a bit during the transition to v2

### Basic Format

| Key | Description | Type | Notes |
| :--- | :--- | :--- | :--- |
| payload | This will always be ”event” in FatesHook | String | None |
| event | This is the name of the event in question | String | None |
| context | This is the extra information about your event.  | Object | Different events have different key value pairs |
| bot_id | This is the corresponding Bot ID of the event | Snowflake? | Only sent when dealing with bors |
| guild_id | This is the corresponding Guild ID of the event | Snowflake? | Only sent when dealing with servers/guilds |
| event_id | This is the event ID of the event in question | UUID | None |
| type | What type of entity you are dealing with (whether its a bot or a guild) | String | Will either be ”bot” or ”guild” depending on the entity. |
| mode | This tells you the mode and allows you to quickly check between ”FC” (FatesHook) or ”VOTE” (Vote Webhook) | String | None |

### Base Event Context

All events in Fates List share the basic format in the below table. If it does mot, then you have 99% found a bug and you should report it on the support server. Additional key valie pairs may be present and these will be noted below.

| Key | Value | Typw |
| :--- | :--- | :--- |
| user | This is the User ID responsible for the event | Snowflake |

### Special Event Contexts

If an event does not appear here, then it uses rhe simple base context format.

#### Reviews

The context of a new review or a edit review event is a [Partial Review](../structures/partial-review.md) of the review and if the event is new review or edit review, all the [Reviews](../structures/review.md) of the bot or server as well (which has every review of your bot or server including the newly added or edited one. Note that all the reviews is only sent on new review and edit review)
