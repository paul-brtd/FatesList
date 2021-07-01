# API v2 beta 3 (June 15th, 2021)

### Changes

* Get Votes API now also returns the timestamp under vts as a epoch. It also returns whether you are getting a partial object, the type of object you are getting and the reason. Providing no User ID now simply returns how many votes your bot has
* Due to the above change to Get Votes, the Timestamped Votes API has been removed. This also means that it is no longer possible to get every User ID-Timestamp for your bot without first knowing the User ID
* API Restructure/Reorganize begin: This is not yet done, but will soon be done. All API endpoints will now be categorized in the docs
* Get User API was renamed to Fetch User API
* Get Login Link and Login User API was added meaning you can now login using the API (more info in the [Custom Clients](../advanced/custom-clients.md) section). The main purpose for this is for Lynx.
* Create Votes API was added allowing you to potentially vote using the API (though its main purpose is actually for Lynx)

### Fixes

* The API is now much faster
* Stability improvements
