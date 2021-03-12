from django.contrib import admin
from django import forms
from .models import *

class FADMIN(admin.ModelAdmin):
    pass

def bot_id(obj):
    return obj.bot_id
bot_id.short_description = 'Bot ID'

def user_id(obj):
    return obj.user_id
user_id.short_description = 'User ID'


class BotVoterAdmin(FADMIN):
    list_display = (bot_id, user_id)

# Register your models here.
admin.site.register(Bot, FADMIN)
admin.site.register(BotVoter, BotVoterAdmin)
admin.site.register(Vanity, FADMIN)
admin.site.register(Server, FADMIN)
