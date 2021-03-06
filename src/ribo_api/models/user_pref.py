from django.db import models
from django.conf import settings
from .usertypes import *

class UserPref(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    pref_id = PositiveTinyIntegerField(default=0)
    pref_value = models.CharField(max_length=255, default="")
    extra_param = models.CharField(max_length=255, default="")
    
    class Meta:
        db_table = 'ribo_users_prefs'