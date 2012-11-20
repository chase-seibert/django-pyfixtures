import re
import datetime
from django.db import models as django_models
from django.conf import settings
from django.core.serializers import python
from django.utils.encoding import smart_unicode
from django.core.serializers import base
from django.db.models import get_apps
from django.db.models import get_models
from django.contrib.contenttypes.models import ContentType


class Serializer(python.Serializer):
    """
    Serializes a QuerySet to Django ORM Model constructors
    """

    DO_PK = True
    DO_SORT = True
    DEFAULT_IMPORTS = [
        'import datetime',
        'from decimal import Decimal',
        'from django.contrib.contenttypes.models import ContentType']

    internal_use_only = False
    model_classes = None
    fks, m2m, vars_placed = None, None, None

    def __init__(self, *args, **kwargs):
        self.DO_SORT = kwargs.get('sort', True)

    def start_serialization(self):
        self.model_classes = {}
        self.fks, self.m2m = [], []
        for app in get_apps():
            for model in get_models(app):
                self.model_classes[smart_unicode(model._meta)] = model  # key == activities.activity, etc
        super(Serializer, self).start_serialization()

    def gen_var_name(self, model_class, pk):
        ''' creates a pythonic variable name from the ModelClass and the pk '''
        var = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', '%s%s' % (model_class.__name__, pk))
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', var).lower()

    def format_fields(self, model_class, pk, fields):
        ''' Outputs the code block inside a particular model declaration, specifying
        all the fields that need to be set. Fields that are set to the default to not
        need to be specified. Try to use references to previously created variables for
        foreign keys. If that is not possible due to circular references, use the IDs. '''

        code = []  # list of key/value tuples

        if pk and self.DO_PK:
            # NOT just 'pk' for the name; some abc models require ptr_id
            code.append((model_class._meta.pk.attname, repr(pk)))

        for (k, v) in fields.items():

            field_meta = model_class._meta.get_field(k)

            if v in (None, field_meta.default):
                continue

            if (model_class, k) in self.fks:
                var_name = self.gen_var_name(field_meta.rel.to, v)
                if field_meta.rel.to.__name__ == 'ContentType':
                    # if you have a fk to django_content_type, turn ID into dynamic orm.get()
                    # this is necessary because ContentType.ID can change on every syncdb
                    content_type = ContentType.objects.get(id=v)
                    code.append((k, 'ContentType.objects.get(app_label="%s", model="%s")' % (
                        content_type.app_label, content_type.model)))
                elif var_name in self.vars_placed:
                    code.append((k, var_name))  # NOT repr
                else:
                    code.append((k + '_id', repr(v)))
            else:
                code.append((k, repr(v)))

        return ',\n    '.join("%s=%s" % (k, v) for (k, v) in code)

    def getvalue(self):
        ''' From a list of objects from the parent class, output python code with imports to
        generate those objects. As it goes through each object in the list, keeps track of
        which Model classes it has seen (and which imports it needs), as well as which model
        instance it has already created. '''

        imports, models = [], []
        imports.extend(self.DEFAULT_IMPORTS)

        seen_imports, self.vars_placed = [], []

        objects = self.objects
        if self.DO_SORT:
            objects = self.sort_dependency_order(self.objects)

        for obj in objects:

            model_class = self.model_classes.get(obj.get('model'))
            if model_class not in seen_imports:

                imports.append('from %s import %s' % (model_class.__module__, model_class.__name__))
                seen_imports.append(model_class)

                concrete_model = model_class._meta.concrete_model
                for field in concrete_model._meta.local_fields:
                    if field.rel:
                        self.fks.append((model_class, field.name))
                for field in concrete_model._meta.many_to_many:
                    self.m2m.append((model_class, field.name))

            pk = obj.get('pk')
            var_name = self.gen_var_name(model_class, pk)
            fields = dict((k, v) for (k, v) in obj.get('fields').items() if (model_class, k) not in self.m2m)
            models.append('%s = %s(\n    %s)\n' % (
                var_name,
                model_class.__name__,
                self.format_fields(model_class, pk, fields)))

            # many to many, can't just call .add(), because the object need to be saved first for that
            m2m_data = dict((k, v) for (k, v) in obj.get('fields').items() if (model_class, k) in self.m2m and v)
            if m2m_data:
                models.append('%s.m2m_data = %r\n' % (var_name, m2m_data))

            # recorded so we know whether we can use it in another object definition
            self.vars_placed.append(var_name)

        return """# auto-generated on %(date)s with %(num_models)s models

%(imports)s


%(models)s""" % dict(imports='\n'.join(imports),
        models='\n'.join(models),
        date=datetime.datetime.now(),
        num_models=len(models))

    def sort_dependency_order(self, objects):
        ''' models in the fixture need to be in order, with the models that depend
        on other models AFTER those other models in the fixture, so they can be
        referred to by name, and also so that the fixture works properly w/ fks enabled.
        There is a very real possibility that we cannot determine an order due to circular
        dependencies. In that case, dumpdata will generate an error message, anf the user
        will need to set PYFIXTURES_CIRCULAR_DEP_BREAKERS to decide which objects should
        be creating using pks instead of references. '''

        sorted_objects = []

        model_deps, seen_models = [], []
        for obj in objects:

            model = self.model_classes.get(obj.get('model'))
            obj['_model'] = model  # for faster access bellow

            if model not in seen_models:

                deps = []
                for field in model._meta.fields:
                    if hasattr(field.rel, 'to'):
                        deps.append(field.rel.to)
                for field in model._meta.many_to_many:
                    deps.append(field.rel.to)

                if model.__name__ in getattr(settings, 'PYFIXTURES_CIRCULAR_DEP_BREAKERS', []):
                    model_deps.append((model, []))
                else:
                    model_deps.append((model, [d for d in list(set(deps)) if d != model]))

                seen_models.append(model)

        found = True
        while model_deps and found:
            found = False
            for (model, deps) in model_deps:
                if deps == []:

                    remove_model = model
                    # remove this model from the list all together
                    model_deps = [(m, d) for (m, d) in model_deps if m != remove_model]
                    # remove this models from the list of dependencies for other models
                    model_deps = [(m, [d for d in dlist if d != remove_model]) for (m, dlist) in model_deps]
                    # there are also dependencies for which there is no data
                    top_level_deps = [m for (m, d) in model_deps]
                    model_deps = [(m, [d for d in dlist if d in top_level_deps]) for (m, dlist) in model_deps]

                    sorted_objects.extend([o for o in objects if o['_model'] == remove_model])
                    found = True
                    break

        if len(objects) != len(sorted_objects):

            for (model, deps) in model_deps:
                print model.__name__, 'depends on', [d.__name__ for d in deps]

            raise base.SerializationError('Could not sort objects in dependency order, is there a circular dependency?')

        for obj in sorted_objects:
            del obj['_model']  # remove temp var

        return sorted_objects


def Deserializer(file, **options):
    ''' Execs the python fixture, and returns an iterator of objects that loaddata can save.
    Pretty dangerous; this may be why this functionality is not built-in to Django. '''
    exec file
    #objects = locals().get('objects')
    # even if these are not strictly in order, the sub-references will be saved on demand
    objects = [v for v in locals().values() if isinstance(v, django_models.Model)]
    for obj in objects:
        yield base.DeserializedObject(obj, getattr(obj, 'm2m_data', {}))
