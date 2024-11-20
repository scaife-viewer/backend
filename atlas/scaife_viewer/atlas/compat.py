"""
@@@ graphene-django does not yet support `django_jsonfield_backport`

ref https://github.com/graphql-python/graphene-django/pull/1017
"""

from django.db.models import JSONField
from graphene_django.converter import (
    convert_django_field,
    convert_json_field_to_string,
)


@convert_django_field.register(JSONField)
def convert_jsonfield_to_string(field, registry=None):
    return convert_json_field_to_string(field, registry=registry)
