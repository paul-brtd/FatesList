# API v2 beta 2 (April 5th, 2021)

### Changes

* Renamed `/api/bots/ext/index` to `/api/index/bots` (pinned: `/api/v2/index/bots`)
* Renamed `/api/bots/ext/search` to `/api/search/bots` (pinned: `/api/v2/search/bots`)
* Added `/api/search/profiles` (pinned: `/api/v2/search/profiles`) for Profile Search
* Added Add Bot (POST `/api/bots/BOTID`, pinned: `/api/v2/bots/BOTID`) and Edit Bot (PATCH `/api/bots/BOTID`, pinned: `/api/v2/bots/BOTID`)
* Most (if not all) PUT requests are now POST, some parameter and endpoint names and routes have either changed, split or have been added, read the endpoint documentation at [Endpoints](../basics/endpoints.md) for more information on what has changed
* Added proper API versioning to ensure such rough transitions do not happen again.
* Timestamped Votes API no longer sends payload: timestamp at the start of the JSON
* Getting reviews is now a seperate endpoint at `/api/bots/BOTID/reviews` (pinned: `/api/v2/bots/BOTID/reviews`)
* Getting promotions and maintenance mode are similarly seperate endpoints

### Fixes

* Regenerate Bot Token API now works and doesn’t error with a 500
* Timestamped Votes API now works and doesn’t error with a 500
* Timestamped Votes API no longer sends payload: timestamp at the start of the JSON

