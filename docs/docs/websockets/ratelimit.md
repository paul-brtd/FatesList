# Ratelimits

Ratelimits are, as of right now, applied on the **IDENTIFY** step of connecting to the WebSocket API. They are silent meaning you will not know that you have been ratelimited and will appear as a no auth error or your bot being skipped if you have multiple

The ratelimits below are the potential ratelimits for Fates List. They keep changing so don't hardcode them and be sure to wait at least 65-80 seconds between each IDENTITY to avoid it:

1. You can only connect to the WS 100 times per day, so use each IDENTITY wisely
2. For burst authentication (where your websocket drops, you must reconnect within 5 seconds or you will be forced to wait the normal time between identities
3. You must wait 65 seconds between identities unless its a burst authentication within 5 seconds
