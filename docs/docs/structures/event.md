# Events

All Events are made of two parts. The metadata (m) and the context (ctx). Keys outside this is not considered part of the event and is extra, usuallt for convenience of the developer.

Metadata

| Key | Description | Type |
| :--- | :--- | :--- |
| e | Event Name (see [here](https://github.com/Fates-List/FatesList/blob/cf339725f2f3082eae39dc03b67be8807a782efb/modules/models/enums.py#L59)) | Integer |
| eid | Event ID (random on websocket auth) | UUID |
| t | Event Type (multi) | Integer/List |
| id | Target Bot/User ID | Snowflake |
| ts | Event Timestamp | Float |
| wt | Webhook Type (Webhook Only) (see [here](https://github.com/Fates-List/FatesList/blob/cf339725f2f3082eae39dc03b67be8807a782efb/modules/models/enums.py#L14)) | Integer |

**Key** 

multi:  List can be returned if multiple choices are present

Context

The context of a event is different per event, but will mostly have a "user" key (type is Snowflake) with the user ID the action applies to.
