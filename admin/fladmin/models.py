# Create your models here.
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django import forms
from django.contrib.postgres.fields import ArrayField
from django.contrib.contenttypes.models import ContentType
import uuid

class ApiEvent(models.Model):
    id = models.UUIDField(primary_key=True)
    bot_id = models.BigIntegerField()
    events = models.TextField()  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'api_event'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class BotCommands(models.Model):
    id = models.UUIDField(primary_key=True)
    slash = models.IntegerField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    args = models.TextField(blank=True, null=True)  # This field type is a guess.
    examples = models.TextField(blank=True, null=True)  # This field type is a guess.
    premium_only = models.BooleanField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)  # This field type is a guess.
    doc_link = models.TextField(blank=True, null=True)
    bot_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bot_commands'


class BotMaint(models.Model):
    id = models.UUIDField(primary_key=True)
    bot_id = models.BigIntegerField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    type = models.IntegerField(blank=True, null=True)
    epoch = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bot_maint'


class BotPacks(models.Model):
    id = models.UUIDField(primary_key=True)
    icon = models.TextField(blank=True, null=True)
    banner = models.TextField(blank=True, null=True)
    created_at = models.BigIntegerField(blank=True, null=True)
    owner = models.BigIntegerField(blank=True, null=True)
    api_token = models.TextField(unique=True, blank=True, null=True)
    bots = models.TextField(blank=True, null=True)  # This field type is a guess.
    description = models.TextField(blank=True, null=True)
    name = models.TextField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bot_packs'


class BotPromotions(models.Model):
    id = models.UUIDField(primary_key=True)
    bot_id = models.BigIntegerField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    info = models.TextField(blank=True, null=True)
    css = models.TextField(blank=True, null=True)
    type = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bot_promotions'


class BotReviews(models.Model):
    id = models.UUIDField(primary_key=True)
    bot_id = models.BigIntegerField()
    user_id = models.BigIntegerField()
    star_rating = models.FloatField(blank=True, null=True)
    review_text = models.TextField(blank=True, null=True)
    flagged = models.BooleanField(blank=True, null=True)
    replies = models.TextField(blank=True, null=True)  # This field type is a guess.
    epoch = models.TextField(blank=True, null=True)  # This field type is a guess.
    review_upvotes = models.TextField(blank=True, null=True)  # This field type is a guess.
    review_downvotes = models.TextField(blank=True, null=True)  # This field type is a guess.
    reply = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bot_reviews'


class BotStatsVotes(models.Model):
    bot_id = models.BigIntegerField(blank=True, null=True)
    total_votes = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bot_stats_votes'


class BotStatsVotesPm(models.Model):
    bot_id = models.BigIntegerField(blank=True, null=True)
    votes = models.BigIntegerField(blank=True, null=True)
    epoch = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bot_stats_votes_pm'


class BotVoter(models.Model):
    id = models.IntegerField(blank=True, primary_key = True)
    bot_id = models.BigIntegerField(blank=True)
    user_id = models.BigIntegerField(blank=True)
    timestamps = ArrayField(base_field = models.BigIntegerField(), blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bot_voters'
        ordering = ['pk']

    def __str__(self):
        return f"{self.id}. BID: {self.bot_id}, UID: {self.user_id}"


class Bot(models.Model):
    """
    This is a bot on Fates List
    """
    bot_id = models.BigIntegerField(primary_key = True)
    prefix = models.CharField(blank=False, null=False, max_length = 9)
    votes = models.BigIntegerField(blank=True, null=True, help_text = "Changing this for no reason may/will lead to punishment such as getting kicked off the staff team or demoted or temporary forced LOA (Leave of absence)")
    servers = models.BigIntegerField(blank=True, null=True)
    shard_count = models.BigIntegerField(blank=True, null=True)
    bot_library = models.CharField(blank=False, null=False, max_length=32)
    webhook = models.CharField(blank=True, null=True, max_length = 1024)
    webhook_type = models.CharField(max_length=10, choices = (
        ('VOTE', 'Vote'),
        ('DISCORD', 'Discord Integration'),
        ('FC', 'Fates Client')
    ))
    description = models.CharField(blank=False, null=False, max_length = 105)
    api_token = models.CharField(unique=True, blank=False, null=False, default = uuid.uuid4, max_length = 255)
    website = models.CharField(blank=True, null=True, max_length = 1024)
    discord = models.CharField(blank=True, null=True, max_length=32)
    tags = ArrayField(base_field = models.TextField(), blank=False, null=False)
    state = models.IntegerField(blank=False, null=False, default=1, help_text = "Use fateslist.xyz main admin console to verify bots", choices = (
        (0, 'Verified'),
        (1, 'Pending Verification'),
        (2, 'Denied'),
        (3, 'Hidden (Cannot be set in client)'),
        (4, 'Banned'),
        (5, 'Under Review'),
        (6, 'Certified')
    ))
    banner = models.CharField(blank=True, null=True, max_length = 1024)
    created_at = models.BigIntegerField(blank=True, null=True)
    invite = models.CharField(blank=True, null=True, max_length=256)
    github = models.CharField(blank=True, null=True, max_length=256)
    features = ArrayField(base_field = models.TextField(), blank=True, null=True)
    private = models.BooleanField(blank=True, null=True)
    html_long_description = models.BooleanField(blank=True, null=False)
    invite_amount = models.IntegerField(blank=True, null=True)
    user_count = models.BigIntegerField(blank=True, null=True)
    css = models.TextField(blank=True, null=True)
    shards = ArrayField(base_field = models.IntegerField(), blank=True, null=True)
    donate = models.CharField(blank=True, null=True, max_length=256)
    username_cached = models.CharField(blank=True, null=False, max_length=32, editable = False)
    long_description = models.TextField(blank=False, null=False)
    privacy_policy = models.TextField(blank = True, null = True)

    class Meta:
        managed = False
        db_table = 'bots'

    def __str__(self):
        return f"{self.username_cached} ({self.bot_id})"

class BotOwner(models.Model):
    id = models.AutoField(primary_key = True)
    bot_id = models.BigIntegerField(blank = True)
    owner = models.BigIntegerField()
    main = models.BooleanField()

    class Meta:
        managed = False
        db_table = "bot_owner"

class Server(models.Model):
    name_cached = models.TextField(blank=True, null=False, editable = False)
    guild_id = models.BigIntegerField(unique=True, primary_key = True)
    votes = models.BigIntegerField(blank=True, null=True)
    webhook_type = models.TextField(blank=True, null=True)
    webhook = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    long_description = models.TextField(blank=True, null=True)
    html_long_description = models.BooleanField(blank=True, null=True)
    css = models.TextField(blank=True, null=True)
    api_token = models.TextField(unique=True, blank=True, null=True)
    website = models.TextField(blank=True, null=True)
    tags = ArrayField(base_field = models.TextField(), blank=True, null=True)
    certified = models.BooleanField(blank=True, null=True)
    created_at = models.BigIntegerField(blank=True, null=True)
    state = models.BooleanField(blank=True, null=True)
    invite_amount = models.IntegerField(blank=True, null=True)
    user_provided_invite = models.BooleanField(blank=True, null=True)
    invite_code = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'servers'

    def __str__(self):
        return f"{self.name_cached} ({self.guild_id})"

class User(models.Model):
    user_id = models.BigIntegerField(primary_key = True)
    api_token = models.TextField(blank=True, null=True)
    coins = models.IntegerField(blank=False, null=False, default = 0, help_text = "Changing this without permission from a higher up (Admin+) = Potential demotion that is possibly public as well. Admins can ignore this but do not abuse your power or the same will apply to you.")
    vote_epoch = models.BigIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    badges = ArrayField(base_field = models.TextField(), blank=True, null=True) 
    username = models.TextField(blank=True, null=True)
    avatar = models.TextField(blank=True, null=True)
    css = models.TextField(blank=True, null=True)
    state = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'


class Vanity(models.Model):
    type = models.IntegerField(blank=True, null=True)
    vanity_url = models.TextField(blank=True, unique=True)
    redirect = models.BigIntegerField(unique=True, blank=True, primary_key = True, editable = False)

    class Meta:
        managed = False
        db_table = 'vanity'

    def __str__(self):
        base = f"{self.redirect}"
        if self.vanity_url == "" or self.vanity_url is None:
            vanity = "No Vanity URL set"
        else:
            vanity = self.vanity_url
        return f"{base} - {vanity}"

class DjangoContentType(ContentType):
    pass

# ULA
import uuid
from .ulaconfig import *

# Create your models here.

class ULABotList(models.Model):
    icon = models.TextField(blank=True, null=True)
    url = models.TextField(unique=True, primary_key = True)
    api_url = models.TextField(blank=True, null=True)
    discord = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    supported_features = ArrayField(base_field = models.IntegerField(), blank=True, null=True)
    api_token = models.TextField(blank=False, null=False, default = uuid.uuid4())
    queue = models.BooleanField(blank=False, null=False, default=False)
    owners = ArrayField(base_field = models.BigIntegerField(), blank=False, null=False, default=list)

    class Meta:
        managed = False
        db_table = 'bot_list'

    def __str__(self):
        return self.url


class ULABotListApi(models.Model):
    id = models.AutoField(primary_key = True)
    url = models.ForeignKey(ULABotList, on_delete = models.CASCADE, db_column = 'url', db_constraint = False, unique = False, db_index = False, blank = True)
    method = models.IntegerField(blank=False, null=False, choices = method_choices, default=1)
    feature = models.IntegerField(blank=False, null=False, choices = feature_choices, default=1)
    supported_fields = models.JSONField(blank=True, null=True, help_text = 'Format of each key, valae is NGBB_KEY: LIST_KEY where NGBB_KEY is the key used by NGBB and LIST_KEY is the key used by the list')
    api_path = models.TextField(blank=False, null=False, default="")

    class Meta:
        managed = False
        db_table = 'bot_list_api'


class ULABotListFeature(models.Model):
    feature_id = models.IntegerField(primary_key = True)
    name = models.TextField(unique=True)
    iname = models.TextField(unique=True, verbose_name = "Internal Name")
    description = models.TextField(blank=True, null=True)
    positive = models.IntegerField(blank=False, null=False, choices = positive_choices)

    class Meta:
        managed = False
        db_table = 'bot_list_feature'

    def __str__(self):
        return self.name

class ULAUser(models.Model):
    user_id = models.BigIntegerField(primary_key = True)
    api_token = models.TextField(unique=True)

    class Meta:
        managed = False
        db_table = "ula_user"

    def __str__(self):
        return str(self.user_id)
