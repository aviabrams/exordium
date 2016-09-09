#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

from dynamic_preferences.types import StringPreference, Section
from dynamic_preferences.registries import global_preferences_registry

exordium = Section('exordium')

@global_preferences_registry.register
class LibraryPath(StringPreference):
    section = exordium
    name = 'base_path'
    default = '/var/audio'
    verbose_name = 'Exordium Library Base Path'
    help_text = 'Where on the filesystem can music files be found?'

@global_preferences_registry.register
class LibraryUrl(StringPreference):
    section = exordium
    name = 'media_url'
    default = 'http://localhost/media'
    verbose_name = 'Exordium Media URL'
    help_text = 'What is a direct URL to the media directory?'