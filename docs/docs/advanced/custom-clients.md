# Custom Clients

If you wish to, you can make a custom third-party client/frontend for Fates List. This is officially allowed by us and you may ask for support when developing it.

We are working on our own Vue frontend rewrite called Lynx which will use the same topics described here. 
More APIs for more tasks will be added in the coming days/weeks to allow for Lynx.

This page will describe some common tasks that your custom client/frontend should likely do.

### Login

One of the main things you will need to implement is login. To do so:

First send a POST request to /api/oauth (see [Endpoints](endpoints.md) to learn how to do this). You will get a `url` field and this is where you should redorect users to for oauth. You may wish to specify a different redirect uri, do this by setting the `oauth_redirect` field. For custom clients, you will also need to set the `ec` field as a dict with the following:

| Key | Description | Type |
| :--- | :--- | :--- |
| post | The url to redirect the user to after oauth and callback auth. | String |
| key | The key that is tied to your custom client. To create this, just use `utils/gensecret.py` | String |
| name | The name of the custom client. Will be displayed in callback auth | String |

The URL, on a `GET` request with the `FL-Keycheck` header set to a nonzero number or a string *should* respond with the key you sent in the `key` field and the name you sent in the `name` field. If it does not, the callback will be aborted.

???+ warning
    The `oauth_redirect` field must be either `https://fateslist.xyz/auth/login/confirm` or `https://fateslist.xyz/api/auth/callback` or users will get a `Invalid redirect_uri` error. Use externallcallback for custom clients or WIP clients like Lynx. Externalcallback needs the `ec` field to be set as well (see above)



This will give you the user token (the `token` field), a [BaseUser](basic-structures.md#baseuser) (the `user` field), the user state (the `state` field), whether they have js enabled (the `js_allowed` field), their user css (the `css` field), the site language they have chosen (the `site_lang` field), whether they have been site banned or not (the `banned` field), their access token object (the `access_token` field, you will need to send this on some endpoints) and the url you should redirect users to (the `redirect` field)
