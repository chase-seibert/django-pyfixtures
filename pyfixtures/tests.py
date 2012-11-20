from django.test import TestCase
from django.contrib.sites.models import Site
from pyfixtures.serializer import Serializer
from pyfixtures.serializer import Deserializer


class PyFixturesSerializerTest(TestCase):

    def test_serialize(self):
        Site.objects.all().delete()
        Site(domain='example.com', name='Example Site').save()
        serializer = Serializer()
        actual_python = serializer.serialize(Site.objects.all())
        # ends with to skip auto generated header w/ timestamp
        self.assertTrue(actual_python.endswith('''import datetime
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site


site1 = Site(
    id=1,
    domain=u'example.com',
    name=u'Example Site')
'''))

    def test_deserialize(self):
        fixture_text = '''import datetime
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site


site1 = Site(
    id=1,
    domain=u'example.com',
    name=u'Example Site')
'''
        objects = list(Deserializer(fixture_text))
        site = objects[0].object
        self.assertEquals((site.domain, site.name), ('example.com', 'Example Site'))
