Welcome to django-polymorphic's documentation!
==============================================

Django-polymorphic simplifies using inherited models in Django projects.
When a query is made at the base model, the inherited model classes are returned.

When we store models that inherit from a ``Project`` model...

>>> Project.objects.create(topic="Department Party")
>>> ArtProject.objects.create(topic="Painting with Tim", artist="T. Turner")
>>> ResearchProject.objects.create(topic="Swallow Aerodynamics", supervisor="Dr. Winter")

...and want to retrieve all our projects, the subclassed models are returned!

>>> Project.objects.all()
    [ <Project:         id 1, topic "Department Party">,
      <ArtProject:      id 2, topic "Painting with Tim", artist "T. Turner">,
      <ResearchProject: id 3, topic "Swallow Aerodynamics", supervisor "Dr. Winter"> ]

Using vanilla Django, we get the base class objects, which is rarely what we wanted:

>>> Project.objects.all()
    [ <Project: id 1, topic "Department Party">,
      <Project: id 2, topic "Painting with Tim">,
      <Project: id 3, topic "Swallow Aerodynamics"> ]

Features
--------

* Full admin integration.
* ORM integration:

 * Support for ForeignKey, ManyToManyField, OneToOneField descriptors.
 * Support for proxy models.
 * Filtering/ordering of inherited models (``ArtProject___artist``).
 * Filtering model types: ``instance_of(...)`` and ``not_instance_of(...)``
 * Combining querysets of different models (``qs3 = qs1 | qs2``)
 * Support for custom user-defined managers.

* Uses the minimum amount of queries needed to fetch the inherited models.
* Disabling polymorphic behavior when needed.


Getting started
---------------

.. toctree::
   :maxdepth: 2

   quickstart
   admin
   performance

Advanced topics
---------------

.. toctree::
   :maxdepth: 2

   advanced
   managers
   third-party
   changelog
   contributing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

