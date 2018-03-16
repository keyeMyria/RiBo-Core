from mongoengine import fields
from django.conf import settings
from mongoengine.queryset.manager import queryset_manager

from ribo_api.models.timestamped import TimeStampedModel


class Api(TimeStampedModel):
    expire_time = fields.DateTimeField(auto_now=False, default=settings.REST_FRAMEWORK['EXPIRED_FOREVER'])
    access_token = fields.StringField(required=True)
    refresh_token = fields.StringField(required=True)
    json = fields.StringField(default=None)
    user_id = fields.ObjectIdField(required=True)
    device = fields.StringField(max_length=64)
    version = fields.StringField(max_length=40)
    type = fields.IntField(default=0)
    app_id = fields.StringField(max_length=64, default='')

    class Meta:
        db_table = 'ribo_apis'
        app_label = 'no_sql'