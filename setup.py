#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-exordium',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    license='BSD License',
    description='A Django-based readonly web music library application.',
    long_description=README,
    url='https://apocalyptech.com/exordium/',
    author='CJ Kucera',
    author_email='pez@apocalyptech.com',
    install_requires=[
        'django',
        'mutagen',
        'Pillow',
        'django-tables2',
        'django-dynamic-preferences',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.10',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)

