CREATE TABLE bots (
    bot_id bigint,
    votes bigint,
    servers bigint,
    shard_count bigint,
    bot_library text,
    webhook text,
    description text,
    long_description text,
    prefix text,
    api_token text,
    website text,
    discord text,
    tags text[],
    certified boolean DEFAULT false,
    queue boolean DEFAULT true,
    banner text DEFAULT 'none'::text,
    created_at bigint,
    owner bigint,
    extra_owners text,
    invite text,
    queue_username text,
    queue_avatar text
);

CREATE TABLE users (
    userid bigint,
    token text,
    vote_epoch bigint
);

CREATE TABLE bot_cache (
    bot_id bigint,
    username text,
    avatar text,
    epoch bigint,
    valid boolean,
    valid_for text
);
