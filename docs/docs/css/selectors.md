# Selectors

**Key**

TYPE() means that there are many TYPEs as subchildren of this object and TYPE[] means that there are multiple of these TYPES retrieved as an array and not as subchildren when you use document.querySelectorAll on it. TYPE{} means both and is equivalent to TYPE()[]. Anything in bold is a variable and you should see the description for information about it.

| Name | Description | Tag  | Type | Object | Selector |
| :--- | :--- | :--- | :--- | :--- | :--- |
| bot-content | The entire div your bot page is in | div | id | Bot | #bot-content |
| bot-avatar | The bots avatar | img | id | Avatar | #bot-avatar |
| bot-username | The bots username | h3 | id | Username | #bot-username |
| bot-description | Your bots short description | h3 | id | Description | #bot-description |
| bot-buttons | The main buttons. If you want to change an individual button, .bot-buttons-**button_name** | div | id | Button() | #bot-buttons |
| bot-buttons-**button_name** | A specific button, see the [Buttons](../buttons) section for more information on button names | button | id | Button | #bot-buttons-**button_name** |
| bot-key-container | The div containing tags and promotions both | div | id | KeyContainer | #bot-key-container |
| bot-tags | The div containing all your tags and the header | div | id | Tag() | #bot-tags |
| bot-tags-header | The "Tags" part of the tags | h5 | id | TagHeader | #bot-tags-header |
| bot-tags-container | The div inside #bot-tags that contains just the tags (not the header) | div | id | TagInner() | #bot-tags-container |
| bot-tags-container-inner | The div inside #bot-tags-container to help position the tags | div | id | Tag() | #bot-tags-container-inner |
| bot-tags-**tag_name**-button | The actual tag, see the [Tags](../tags) section for more information on tag names | button | id  | TagButton | #bot-tags-**tag_name**-button |
| bot-promo | This is the div containing all promotions | div | id | PromoFull | #bot-promo |
| bot-promo-header | This is the header of all the promotions (the Special Promotions/Events) | h5 | id  | PromoHeader | #bot-promo-header |
| bot-promo-container | This is the container for a promo | div[] | class | Promotion[] | .bot-promo-container |
| bot-promo-container-**index** | This is one promo based on jinja2 loop.index which is a number going from 0 to the N-1th promo index | div | id | Promotion | #bot-promo-container-**index** |
| bot-long-description | The bots long description. All links are given the long-desc-link class (selector: .long-desc-link) | div | id | LongDescription | #bot-long-description |
| bot-long-description-container | The container around the long description | div | id | LongDescriptionContainer | #bot-long-description-container |
| long-desc-link | All links in long descriptiom get this class making it grey by default. Use ldlink class instead as this class causes side effects | a[] | class | LongDescriptionInternalLink[] | .long-desc-link |
| ldlink | All links in long description get this as well. It is highly recommended to use this over long-desc-link as this doesn’t break other things in your bot page | a[] | class | LongDescriptionLink[] | .ldlink |
| bot-switcher | This is the bot switcher (The Description, Review, Commands, About and Admin tabs) | div | id | BotSwitcher | #bot-switcher |
| tablinks | All of the tabs currently | button[] | class | Tab[] | .tablinks |
| bot-**tab_name**-tab-button | The actual switcher tab, see the [Switcher Tabs](tabs.md) section for more information on the tab names  | button | id | Tab | #bot-**tab_name**-tab-button |
| review_form | This is the review form used when making reviews. It is internal and is only being documented to be complete. Do not change this unless absolutely needed | form | id | _ReviewForm | #review_form |
| reviewreply-**review_id** | This is the review form used when making replies to reviews. It is internal and is only being documented to be complete. Do not change this unless absolutely needed. The review id here is the id of the review you are trying to reply to. | form | id | _ReviewReply | #reviewreply-**review_id** |
| review-**review_id** | This is the review form used when editing reviews. It is internal and is only being documented to be complete. Do not change this unless absolutely needed. The review id here is the id of the review you are trying to edit. | form | id | _ReviewEdit | #review-**review_id** |
| bot-review-header | This is the review header (The place with stars and the edit link) | div[] | class | ReviewHeader[] | .bot-review-header |
| bot-review-user | This is the main review comtainer | div{} | class | ReviewUser{} | .bot-review-user |
| bot-reviews | The bot review container | div | id | BotReviews | #bot-reviews |
| bot-range-slider | The slider for the creatiom and editing of bot reviews and replies. | input[] | class | BotRangeSlider[] | .bot-range-slider |
