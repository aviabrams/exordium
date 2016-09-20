#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

from django.utils.timezone import get_current_timezone
from django.core.management.base import BaseCommand, CommandError
from exordium.models import Album

import re
import getpass
import datetime

# We don't want this subcommand to give someone grief if they don't have
# mysql.connector installed
try:
    import mysql.connector
    from mysql.connector.errors import InterfaceError, ProgrammingError
    have_mysql = True
except ImportError:
    have_mysql = False

class Command(BaseCommand):

    # Help text
    help = 'Imports album addition times from an existing MySQL Ampache database'

    # Ampache uses a much wider set of prefixes than we do, and strips them out
    # of album names as well.  This can be customized in the Ampache config, so
    # perhaps we should have this be an argument, but this is the default, and
    # for now we'll just do it this way.
    prefixre = re.compile('^((The|An|A|Die|Das|Ein|Eine|Les|Le|La) )?(.*)$', re.IGNORECASE)

    def add_arguments(self, parser):
        parser.add_argument('--dbhost',
                required=True,
                type=str,
                help='MySQL host to connect to')
        parser.add_argument('--dbname',
                required=True,
                type=str,
                help='MySQL database name to connect to')
        parser.add_argument('--dbuser',
                required=True,
                type=str,
                help='MySQL user to connect with (password will be prompted)')

    def strip_prefix(self, name):
        """
        Strip the ampache prefix off of the given name.
        """
        match = self.prefixre.match(name)
        if match.group(3):
            return match.group(3)
        else:
            return name

    def handle(self, *args, **options):
        global have_mysql
        if not have_mysql:
            raise CommandError('mysql.connector library is not present, aborting')

        # Get our db password
        dbpass = getpass.getpass(prompt='Database Password: ')

        # Get our timezone.  We're assuming, of course, that Ampache is storing the
        # timestamp in the same timezone as Django is using.  This happens to be
        # correct for myself, at least.
        tz = get_current_timezone()

        # Connect to the database
        try:
            cx = mysql.connector.connect(host=options['dbhost'],
                database=options['dbname'],
                user=options['dbuser'],
                password=dbpass)
        except (InterfaceError, ProgrammingError) as e:
            raise CommandError('Could not connect to MySQL: %s' % (e))
        curs = cx.cursor(dictionary=True)

        # Now do our work
        updated = 0
        ampache_artists = {}
        albums = Album.objects.all()
        for album in albums:

            # If we're a V/A album, our best bet is to get the artist from the album's
            # first track, since Ampache doesn't have "Various" in its database
            if album.artist.name == 'Various':
                song = album.song_set.all()[0]
                artist_to_use = song.artist.name
                #if 'Christmas Remixed : Holiday Classics Re-Grooved' in album.name:
                #if album.name == "Christmas Remixed : Holiday Classics Re-Grooved\x00":
                #    print('Picked artist "%s" for "%s"' % (artist_to_use, album.name))
            else:
                artist_to_use = album.artist.name
            
            # Get the Ampache artist ID
            album_artist_name = self.strip_prefix(artist_to_use)
            if album_artist_name not in ampache_artists:
                curs.execute('select id, name from artist where name=%s', (album_artist_name,))
                row = curs.fetchone()
                if row:
                    ampache_artists[album_artist_name] = row['id']
                else:
                    self.stdout.write('ERROR: Could not find information for artist "%s"' % (album.artist))
                    continue

            # Ampache uses 'Unknown (Orphaned)' for non-album tracks
            if 'Non-Album Tracks' in album.name:
                album_name = 'Unknown (Orphaned)'
            else:
                album_name = self.strip_prefix(album.name)

                # There are a few tracks in my library which end up reporting a NUL char as the
                # last character of the album name, which Ampache is stripping out.  I should
                # probably do the same in Exordium, but for now, just strip it out here.
                while album_name[-1] == "\x00":
                    album_name = album_name[:-1]

            # Now get the album addition time (Note that Ampache stores this information
            # only in the song record itself.  Also note that Ampache does NOT associate
            # an artist directly to an album!)
            curs.execute('select s.addition_time from song s, album a where s.artist=%s and a.name=%s and s.album=a.id order by s.id limit 1',
                (ampache_artists[album_artist_name], album_name,))
            row = curs.fetchone()
            if row:
                timestamp = datetime.datetime.fromtimestamp(row['addition_time'], tz=tz)
                #self.stdout.write('Got addition time "%s" for "%s / %s"' % (timestamp, album.artist, album))
                album.time_added = timestamp
                album.save()
                updated += 1
            else:
                self.stdout.write('ERROR: Could not find addition_time for album "%s / %s"' % (album.artist, album))

        # Clean up
        curs.close()
        cx.close()
        self.stdout.write('Done!  Albums updated: %d' % (updated))
