CREATE DATABASE fateslist;
\c fateslist

CREATE TABLE bots (
    bot_id bigint,
    votes bigint,
    servers bigint,
    shard_count bigint,
    bot_library text,
    webhook text,
    description text,
    long_description text,
    html_long_description boolean default false,
    prefix text,
    features TEXT[] DEFAULT [],
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
    private boolean DEFAULT false;
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

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE api_event (
    id uuid primary key DEFAULT uuid_generate_v4(),
    bot_id bigint,
    events text
);

CREATE TABLE promotions (
   id uuid primary key DEFAULT uuid_generate_v4(),
   bot_id bigint,
   title text,
   info text,
   css text,
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
