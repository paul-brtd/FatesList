CREATE DATABASE fateslist;
\c fateslist
CREATE EXTENSION "uuid-ossp";

CREATE TABLE bots (
    username_cached text DEFAULT '',
    bot_id bigint not null unique,
    votes bigint,
    servers bigint,
    last_stats_post timestamptz NOW(),
    user_count bigint DEFAULT 0,
    shard_count bigint,
    shards integer[] DEFAULT '{}',
    bot_library text,
    webhook_type text DEFAULT 'VOTE',
    webhook text,
    description text,
    long_description text,
    long_description_type integer default 0,
    js_whitelist boolean default false,
    css text default '',
    prefix text,
    features TEXT[] DEFAULT '{}',
    api_token text unique,
    website text,
    discord text,
    tags text[],
    state integer DEFAULT 1,
    banner text DEFAULT 'none'::text,
    created_at timestamptz DEFAULT NOW(),
    invite text,
    invite_amount integer DEFAULT 0,
    github TEXT,
    private boolean DEFAULT false,
    donate text,
    privacy_policy text,
    nsfw boolean DEFAULT false,
    verifier bigint
);

CREATE TABLE bot_tags (
    bot_id BIGINT NOT NULL,
    tag TEXT NOT NULL,
    CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
)

CREATE TABLE bot_owner (
    _id SERIAL,
    bot_id BIGINT not null,
    owner BIGINT,
    main BOOLEAN DEFAULT false,
    CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX bot_owner_index ON bot_owner USING COLUMNSTORE(bot_id, owner, main);

CREATE TABLE bot_packs (
   id uuid primary key DEFAULT uuid_generate_v4(),
   icon text,
   banner text,
   created_at bigint,
   owner bigint,
   api_token text unique,
   bots bigint[],
   description text,
   name text unique
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
   doc_link text, -- link to documentation of command
   CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE bot_stats_votes (
   bot_id bigint,
   total_votes bigint,
   CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
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
   reply boolean default false,
   CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE bot_voters (
    bot_id bigint,
    user_id bigint,
    timestamps timestamptz[] DEFAULT '{NOW()}',
    CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE users (
    id SERIAL,
    user_id bigint,
    api_token text,
    vote_epoch timestamptz,
    description text,
    badges text[],
    username text,
    css text default '',
    state integer default 0, -- 0 = No Ban, 1 = Global Ban
    coins INTEGER DEFAULT 0
);

CREATE TABLE user_payments (
    user_id bigint NOT NULL,
    token TEXT NOT NULL,
    stripe_id TEXT DEFAULT '',
    livemode BOOLEAN DEFAULT FALSE,
    coins INTEGER NOT NULL,
    paid BOOLEAN DEFAULT FALSE
);

CREATE TABLE bot_api_event (
    bot_id BIGINT, 
    epoch BIGINT, 
    event TEXT, 
    context JSONB, 
    id UUID,
    CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE bot_promotions (
   id uuid primary key DEFAULT uuid_generate_v4(),
   bot_id bigint,
   title text,
   info text,
   css text,
   type integer default 3, -- 1 = announcement, 2 = promo, 3 = generic
   CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE bot_maint (
   id uuid primary key DEFAULT uuid_generate_v4(),
   bot_id bigint,
   reason text,
   type integer,
   epoch bigint,
   CONSTRAINT bots_fk FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE vanity (
    id SERIAL,
    type integer, -- 1 = bot, 2 = profile, 3 = server
    vanity_url text unique, -- This is the text I wish to match
    redirect bigint unique, -- What does this vanity resolve to
    redirect_text text unique-- For the future
);

CREATE TABLE servers (
    name_cached text not null,
    guild_id bigint not null unique,
    votes bigint,    
    webhook_type text DEFAULT 'VOTE',
    webhook text,
    description text,
    long_description text,
    long_description_type integer default 0,
    css text default '',
    api_token text unique,
    website text,
    certified boolean DEFAULT false,
    created_at timestamptz,
    invite_amount integer DEFAULT 0,
    user_provided_invite boolean,
    invite_code text,
    state int default 0
)

CREATE TABLE server_tags (
    guild_id bigint not null,
    tag text,
    CONSTRAINT guilds_fk FOREIGN KEY (guild_id) REFERENCES servers(guild_id) ON DELETE CASCADE ON UPDATE CASCADE
)

CREATE TABLE bot_list (
	icon TEXT,
	url TEXT NOT NULL UNIQUE,
	api_url TEXT,
	api_docs TEXT,
	discord TEXT,
	description TEXT,
	supported_features INTEGER[],
	api_token TEXT,
	queue BOOLEAN DEFAULT FALSE,
	owners BIGINT[] DEFAULT '{}'
);

CREATE TABLE bot_list_feature (
	feature_id INTEGER PRIMARY KEY,
	name TEXT NOT NULL UNIQUE,
	iname TEXT NOT NULL UNIQUE, -- Internal Name
	description TEXT,
	positive INTEGER
);

CREATE TABLE bot_list_api (
	id SERIAL PRIMARY KEY, -- Django'isms and good for us
	url TEXT NOT NULL,
	method INTEGER, -- 1 = GET, 2 = POST, 3 = PATCH, 4 = PUT, 5 = DELETE
	feature INTEGER, -- 1 = Get Bot, 2 = Post Stats
	supported_fields JSONB, -- Supported fields
	api_path TEXT NOT NULL,
	CONSTRAINT url_constraint FOREIGN KEY (url) REFERENCES bot_list(url) ON DELETE CASCADE ON UPDATE CASCADE -- Autoupdate
);

CREATE TABLE ula_user (
	user_id BIGINT NOT NULL,
	api_token TEXT NOT NULL UNIQUE
);

