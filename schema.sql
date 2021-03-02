CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE DATABASE fateslist;
\c fateslist

CREATE TABLE bots (
    bot_id bigint,
    votes bigint,
    servers bigint,
    user_count bigint DEFAULT 0,
    shard_count bigint,
    shards integer[] DEFAULT '{}',
    bot_library text,
    webhook_type text DEFAULT 'VOTE',
    webhook text,
    description text,
    long_description text,
    html_long_description boolean default false,
    js_whitelist boolean default false,
    css text default '',
    prefix text,
    features TEXT[] DEFAULT '{}',
    api_token text unique,
    website text,
    discord text,
    tags text[],
    certified boolean DEFAULT false,
    queue boolean DEFAULT true,
    banner text DEFAULT 'none'::text,
    created_at bigint,
    owner bigint,
    extra_owners bigint[],
    invite text,
    invite_amount integer DEFAULT 0,
    banned BOOLEAN DEFAULT false,
    github TEXT,
    private boolean DEFAULT false,
    autovote_whitelist boolean DEFAULT false,
    autovote_whitelisted_users bigint[] DEFAULT [];
);

CREATE TABLE bot_commands (
   id uuid primary key DEFAULT uuid_generate_v4(),
   bot_id bigint,
   slash integer, -- 0 = no, 1 = guild, 2 = global
   name text, -- command name
   description text, -- command description
   args text[], -- list of arguments
   examples text[], -- examples
   premium_only boolean default false, -- premium status
   notes text[], -- notes on said command
   doc_link text -- link to documentation of command
);

CREATE TABLE bot_stats_votes (
   bot_id bigint,
   total_votes bigint
);

CREATE TABLE bot_stats_votes_pm (
   bot_id bigint,
   month integer,
   votes bigint
);

CREATE TABLE bot_reviews (
   id uuid primary key DEFAULT uuid_generate_v4(),
   bot_id bigint not null,
   user_id bigint not null,
   star_rating float4 default 0.0,
   review_text text,
   review_upvotes bigint[] default '{}',
   review_downvotes bigint[] default '{}',
   flagged boolean default false,
   epoch bigint[] default '{}',
   replies uuid[] default '{}',
   reply boolean default false
);

CREATE TABLE bots_voters (
    bot_id bigint,
    userid bigint,
    timestamps bigint[]
);

CREATE TABLE users (
    userid bigint,
    token text,
    vote_epoch bigint,
    description text,
    certified boolean,
    badges text[],
    username text
    css text default '';
);

CREATE TABLE bot_cache (
    bot_id bigint,
    username text,
    avatar text,
    epoch bigint,
    valid boolean,
    valid_for text
);


CREATE TABLE api_event (
    id uuid primary key DEFAULT uuid_generate_v4(),
    bot_id bigint,
    events text[]
);

CREATE TABLE bot_promotions (
   id uuid primary key DEFAULT uuid_generate_v4(),
   bot_id bigint,
   title text,
   info text,
   css text,
   type integer default 3 -- 1 = announcement, 2 = promo, 3 = generic
);

CREATE TABLE bot_maint (
   id uuid primary key DEFAULT uuid_generate_v4(),
   bot_id bigint,
   reason text,
   type integer,
   epoch bigint
);

CREATE TABLE vanity (
    type integer, -- 1 = bot, 2 = profile, 3 =  nothing right now but may be used
    vanity_url text, -- This is the text I wish to match
    redirect bigint unique, -- What does this vanity resolve to
    redirect_text text unique-- For the future
);

CREATE TABLE support_requests (
    id uuid primary key DEFAULT uuid_generate_v4(),
    enquiry_type text,
    resolved boolean default false,
    files bytea[],
    filenames TEXT[],
    title text,
    description text,
    bot_id BIGINT
);

CREATE TABLE servers (
    guild_id bigint not null unique,
    votes bigint,    
    webhook_type text DEFAULT 'VOTE',
    webhook text,
    description text,
    long_description text,
    html_long_description boolean default false,
    css text default '',
    api_token text unique,
    website text,
    tags text[],
    certified boolean DEFAULT false,
    created_at bigint,
    banned BOOLEAN DEFAULT false,
    invite_amount integer DEFAULT 0,
    user_provided_invite boolean,
    invite_code text
)
