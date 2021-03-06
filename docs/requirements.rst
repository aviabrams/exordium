.. Requirements file

Requirements
============

Exordium requires at least Python 3.4 *(tested in 3.4 and 3.5)*,
and Django 1.11.

Exordium makes use of Django's session handling and user backend
mechanisms, both of which are enabled by default.  This shouldn't
be a problem unless they've been purposefully disabled.

Exordium requires the following additional third-party modules:

- mutagen (built on 1.37)
- Pillow (built on 4.1.0)
- django-tables2 (built on 1.5.0)
- django-dynamic-preferences (built on 1.1), which in turn requires:

  - six (built on 1.10.0)
  - persisting_theory (built on 0.2.1)

These requirements may be installed with ``pip``, if Exordium itself hasn't
been installed via ``pip`` or some other method which automatically
installs dependencies::

    pip install -r requirements.txt
