# Custom Clients

If you wish to, you can make a custom third-party client/frontend for Fates List. This is officially allowed by us and you may ask for support when developing it.

We are working on our own Vue frontend rewrite called Lynx which will use the same topics described here. 
More APIs for more tasks will be added in the coming days/weeks to allow for Lynx.

This page will describe some common tasks that your custom client/frontend should likely do.

### Login

One of the main things you will need to implement is login. To do so:

First send a POST request to /api/oauth (see [Endpoints](endpoints.md) to learn how to do this). You will get a `url` field and this is where you should redorect users to for oauth. You may wish to specify a different redirect uri, do this by setting the `oauth_redirect_uri` field.

This will give you the user token (the `token` field), a [BaseUser](basic-structures.md#baseuser) (the `user` field), the user state (the `state` field), whether they have js enabled (the `js_allowed` field), their user css (the `css` field), the site language they have chosen (the `site_lang` field), whether they have been site banned or not (the `banned` field), their access token object (the `access_token` field, you will need to send this on some endpoints) and the url you should redirect users to (the `redirect` field)
