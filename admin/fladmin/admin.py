from django.contrib import admin
from django import forms
from .models import *
from simple_history.admin import SimpleHistoryAdmin

class FADMIN(SimpleHistoryAdmin):
    save_on_top = False

def bot_id(obj):
    return obj.bot_id
bot_id.short_description = 'Bot ID'

def user_id(obj):
    return obj.user_id
user_id.short_description = 'User ID'

def username_cached(obj):
    return obj.username_cached
username_cached.short_description = 'Username'

def username(obj):
    return obj.username
username.short_description = 'Username'

def vanity_url(obj):
    return obj.vanity_url
vanity_url.short_description = "Vanity"

def redirect(obj):
    return obj.redirect
redirect.short_description = "Bot ID"

def type_vanity(obj):
    if obj.type == 1:
        return "Bot"
    elif obj.type == 2:
        return "Profile"
    elif obj.type == 3:
        return "Server"
    else:
        return "Unknown"
type_vanity.short_description = "Type"

class BotVoterAdmin(FADMIN):
    search_fields = ['bot_id', 'user_id']
    list_display = (bot_id, user_id)

class BotAdmin(FADMIN):
    search_fields = ['bot_id', 'username_cached']
    list_display = (bot_id, username_cached)
    def get_readonly_fields(self, request, obj=None):
        if obj: # obj is not None, so this is an edit
            return ['bot_id',] # Return a list or tuple of readonly fields' names
        else: # This is an addition
            return []

class UserAdmin(FADMIN):
    search_fields = ['user_id', 'username']
    list_display = (user_id, username)
    def get_readonly_fields(self, request, obj=None):
        if obj: # obj is not None, so this is an edit
            return ['user_id',] # Return a list or tuple of readonly fields' names
        else: # This is an addition
            return []


class VanityAdmin(FADMIN):
    search_fields = ['redirect', 'vanity_url', 'type']
    list_display = (redirect, vanity_url, type_vanity)

# Register your models here.
admin.site.register(Bot, BotAdmin)
admin.site.register(BotVoter, BotVoterAdmin)
admin.site.register(Vanity, VanityAdmin)
admin.site.register(Server, FADMIN)
admin.site.register(User, UserAdmin)
