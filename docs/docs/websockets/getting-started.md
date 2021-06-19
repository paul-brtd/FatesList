# Getting Started

Fates List offers websockets to allow you to get real time stats about your bot. Before we dive into how it works, here is some basic information

### What are Websockets?

Please read [this nice MDN doc on WebSockets](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API) first before attempting this

### The Steps

We'll go over each step in detail in these docs, but here are the main steps in connecting to the Fates List WebSocket API:

1. **IDENTIFYING** to the API and dealing with errors
2. **LISTENING** for a **READY** event
3. (optional) **Getting old events** using the ws_event API for your bot (exact URL for your bot will be provided in the ready message)
4. **Receiving new events** from the API
5. **Handling duplicate events** and **handling ratelimits**
