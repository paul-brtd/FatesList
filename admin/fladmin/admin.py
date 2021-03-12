from django.contrib import admin
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin
from .models import *

class FADMIN(admin.ModelAdmin, DynamicArrayMixin):
    pass

# Register your models here.
admin.site.register(Bot, FADMIN)
admin.site.register(BotVoter, FADMIN)
admin.site.register(Vanity, FADMIN)
admin.site.register(Server, FADMIN)
