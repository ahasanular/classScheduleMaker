from django.db import models


class TimeStampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class ModelMixin(TimeStampMixin):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
