# About

Django fixtures can lead to maintenance problems. You often forget to update them when you refactor your models. Other times, you have to try to fix them by hand and find yourself in a morass of primary keys. In general, they are fragile.

Many experts suggest that you forgo fixtures and write your own object factories. Great idea! Here is a tool to help you get started. Using the regular Django `dumpdata` command, pyfixtures will generate a python file that contains all the code necessary to re-constitute that data in an empty database. You can take that code and refactor it into something you maintain going forward, or you can re-generate it from a target database when needed.

# Install

### Add to INSTALLED_APPS

In your `settings.py`, add `pyfixtures` to the INSTALLED_APPS setting:

```python
INSTALLED_APPS = (
    ...
    'pyfixtures',
    )
```

### Set SERIALIZATION_MODULES

```bash
SERIALIZATION_MODULES = {'py': 'pyfixtures.serializer'}
```

# Usage

Use the regular Django dumpdata command, but with the format set to pyfixtures.

```bash
./manage.py dumpdata --exclude contenttypes --format=py > fixtures/initial_data.py
```

You can also use the `loaddata` command on that file, as you would expect.

```bash
./manage.py loaddata fixtures/initial_data.py
```

# Settings

```bash
PYFIXTURES_CIRCULAR_DEP_BREAKERS = ('Organization', 'Group', 'WorkflowHistory')
```

If you run into problems serializing your models due to circular dependencies, pyfixtures will prompt you to "break the tie" by designating one or more of your models to use primary keys directly in the constructors.

You'll know if you need to use this setting if you see something like the following when you run dumpdata:

```bash
InfractionType depends on ['WorkflowItem']
WorkflowItem depends on ['WorkflowHistory']
WorkflowHistory depends on ['WorkflowItem']
Error: Unable to serialize database: Could not sort objects in dependency order, is there a circular dependency?
```

# Writing Your own Fixtures

The fixtures are mostly what you would expect. You import models that you need, and declare your objects. The fixtures that we generate don't use loops, but you can if you want to.

Because Django's `loaddata` command expects to save the models itself, we don't call `save()` on the models directly in the fixture. Instead, anything you define in the scope of the fixture file that inherits from Django's Model class will be saved when `loaddata` runs.

This is slightly at odds with how many to many relationships work in Django. Normally, you would structure your code like this:

```python
from django.db import models

class Publication(models.Model):
    title = models.CharField(max_length=30)

class Article(models.Model):
    headline = models.CharField(max_length=100)
    publications = models.ManyToManyField(Publication)

p1 = Publication(title='The Python Journal')
p1.save()

a1 = Article(headline='Django lets you build Web apps easily')
a1.publications.add(p1)
```

Because we need to defer the saving of your models, we use the following mechanism to declare many to many relationships. You should follow this convention if you write your own fixtures.

```python
p1 = Publication(title='The Python Journal')
a1 = Article(headline='Django lets you build Web apps easily')
a1.m2m_data = {'publications': [p1]}
```
