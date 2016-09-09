from django.test import TestCase
from django.urls import reverse

from dynamic_preferences.registries import global_preferences_registry

import os
import shutil
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TDRC, TRCK, TDRL

from .models import Artist, Album, Song, App

# Create your tests here.

# TODO: At the moment all this really does is test the models themselves,
# and more specifically the add() and update() logic.  It does not
# currently test anything relating to views.

class ExordiumTests(TestCase):
    """
    Custom TestCase class for Exordium.  Includes our `initial_data`
    fixture and sets up a pretend library under `testdata`.  Uses
    the sample mp3 files in `testdata` as the basis for all the files
    that we'll be testing with.
    """

    fixtures = ['initial_data.json']

    testdata_path = os.path.join(os.path.dirname(__file__), 'testdata')
    library_path = os.path.join(testdata_path, 'library')

    prefs = None

    def setUp(self):
        """
        Run automatically at the start of any test.  Ensure that there's no
        library hanging around in our testdata dir, ensure that our base
        testing files exist, and then set up the base library path.
        """
        for filename in ['silence-abr.mp3', 'silence-cbr.mp3', 'silence-vbr.mp3', 'invalid-tags.mp3']:
            if not os.path.exists(os.path.join(self.testdata_path, filename)):
                raise Exception('Required testing file "%s" does not exist!' % (filename))
        if os.path.exists(self.library_path):
            raise Exception('Test data path "%s" cannot exist before running tests' %
                (self.library_path))
        os.mkdir(self.library_path)
        self.prefs = global_preferences_registry.manager()
        self.prefs['exordium__base_path'] = self.library_path

    def tearDown(self):
        """
        Run automatically at the test conclusion.  Get rid of our base
        library.
        """
        shutil.rmtree(self.library_path)

    def add_mp3(self, path='', filename='file.mp3', artist='', album='',
            title='', tracknum=0, maxtracks=None, year=0, yeartag='TDRC',
            basefile='silence-vbr.mp3', save_as_v23=False,
            apply_tags=True):
        """
        Adds a new mp3 with the given parameters to our library.

        Pass in `save_as_v23` as `True` to have the file save with an ID3v2.3
        tag, instead of ID3v2.4.  One of the main tag-level changes which
        will happen there is conversion of the year tag to TYER, which
        we'll otherwise not be specifying directly.  `yeartag` is effectively
        ignored when `save_as_v23` is True.

        Pass in `False` for `apply_tags` to only use whatever tags happen to
        be present in the source basefile.
        """
        if path != '' and ('..' in path or path[0] == '/'):
            raise Exception('Given path "%s" is invalid' % (path))

        if '/' in basefile or len(basefile) < 3 or '.' not in basefile:
            raise Exception('Invalid basefile name: %s' % (basefile))

        src_filename = os.path.join(self.testdata_path, basefile)
        if not os.path.exists(src_filename):
            raise Exception('Source filename %s is not found' % (src_filename))

        full_path = os.path.join(self.library_path, path)
        full_filename = os.path.join(full_path, filename)
        os.makedirs(full_path, exist_ok=True)
        shutil.copyfile(src_filename, full_filename)
        self.assertEqual(os.path.exists(full_filename), True)

        # Finish here if we've been told to.
        if not apply_tags:
            return

        # Apply the tags as specified
        tags = ID3()
        tags.add(TPE1(encoding=3, text=artist))
        tags.add(TALB(encoding=3, text=album))
        tags.add(TIT2(encoding=3, text=title))

        if maxtracks is None:
            tags.add(TRCK(encoding=3, text=str(tracknum)))
        else:
            tags.add(TRCK(encoding=3, text='%s/%s' % (tracknum, maxtracks)))

        if yeartag == 'TDRL':
            tags.add(TDRL(encoding=3, text=str(year)))
        elif yeartag == 'TDRC':
            tags.add(TDRC(encoding=3, text=str(year)))
        else:
            raise Exception('Unknown year tag specified: %s' % (yeartag))

        # Convert to ID3v2.3 if requested.
        if save_as_v23:
            tags.update_to_v23()

        # Save to our filename
        tags.save(full_filename)

    def update_mp3(self, filename, artist=None, album=None,
            title=None, tracknum=None, maxtracks=None, year=None):
        """
        Updates an on-disk mp3 with the given tag data.  Any passed-in
        variable set to None will be ignored.  It's possible there could
        be some problems with ID3v2.3 vs. ID3v2.4 tags in here - I don't
        know if mutagen does an auto-convert.  I think it might.

        Will ensure that the file's mtime is updated.
        """

        if len(filename) < 3 or '..' in filename or filename[0] == '/':
            raise Exception('Given filename "%s" is invalid' % (filename))

        full_filename = os.path.join(self.library_path, filename)
        self.assertEqual(os.path.exists(full_filename), True)

        starting_mtime = int(os.stat(full_filename).st_mtime)

        tags = ID3(full_filename)

        if artist is not None:
            tags.delall('TPE1')
            tags.add(TPE1(encoding=3, text=artist))

        if album is not None:
            tags.delall('TALB')
            tags.add(TALB(encoding=3, text=album))

        if title is not None:
            tags.delall('TIT2')
            tags.add(TIT2(encoding=3, text=title))

        if tracknum is not None:
            tags.delall('TRCK')
            if maxtracks is None:
                tags.add(TRCK(encoding=3, text=str(tracknum)))
            else:
                tags.add(TRCK(encoding=3, text='%s/%s' % (tracknum, maxtracks)))

        if year is not None:
            tags.delall('TDRC')
            tags.delall('TDRL')
            tags.delall('TYER')
            tags.add(TDRC(encoding=3, text=str(year)))

        # Save
        tags.save()

        # Check on mtime update and manually fix it if it's not updated
        stat_result = os.stat(full_filename)
        ending_mtime = int(stat_result.st_mtime)
        if starting_mtime == ending_mtime:
            new_mtime = ending_mtime + 1
            os.utime(full_filename, times=(stat_result.st_atime, new_mtime))

    def delete_file(self, filename):
        """
        Deletes the given file from our fake library
        """
        if len(filename) < 3 or '..' in filename or filename[0] == '/':
            raise Exception('Given filename "%s" is invalid' % (filename))

        full_filename = os.path.join(self.library_path, filename)
        self.assertEqual(os.path.exists(full_filename), True)

        os.unlink(full_filename)

        self.assertEqual(os.path.exists(full_filename), False)

    def move_file(self, filename, destination):
        """
        Deletes the given file from our fake library
        """
        if len(filename) < 3 or '..' in filename or filename[0] == '/':
            raise Exception('Given filename "%s" is invalid' % (filename))

        full_filename = os.path.join(self.library_path, filename)
        self.assertEqual(os.path.exists(full_filename), True)

        if destination != '' and ('..' in destination or destination[0] == '/'):
            raise Exception('Given destination "%s" is invalid' % (destination))
        full_destination = os.path.join(self.library_path, destination)

        # Create the destination dir if it doesn't exist
        os.makedirs(full_destination, exist_ok=True)

        # Now move
        shutil.move(full_filename, full_destination)

        dest_filename = os.path.join(full_destination, os.path.basename(filename))
        self.assertEqual(os.path.exists(dest_filename), True)

    def assertNoErrors(self, appresults):
        """
        Given a list of tuples (as returned from `App.add()` or `App.update()`),
        ensure that none of the lines have status App.STATUS_ERROR
        """
        for (status, line) in appresults:
            self.assertNotEqual(status, App.STATUS_ERROR)
        return appresults

    def run_add(self):
        """
        Runs an `add` operation on our library, and checks for errors.
        """
        return self.assertNoErrors(App.add())

    def run_update(self):
        """
        Runs an `update` operation on our library, and checks for errors.
        """
        return self.assertNoErrors(App.update())

class BasicAddTests(ExordiumTests):
    """
    Basic testing of the add() procedure under various circumstances.
    """

    ###
    ### Some methods called by the actual tests to get rid of some duplication
    ###

    def mp3_mode_test(self, mode):
        """
        Tests a simple addition of an mp3 of the given mode
        (abr/cbr/vbr) to the database, to ensure that that detection
        process is working properly.
        """
        self.add_mp3(artist='Artist', title='Title', basefile='silence-%s.mp3' % (mode.lower()))
        self.run_add()
        song = Song.objects.get(title='Title')
        self.assertEquals(song.mode, mode.upper())

    def mp3_year_test(self, year, yeartag):
        """
        Tests a simple addition of an mp3 to the database, using
        the specified year tag.
        """
        self.add_mp3(artist='Artist', title='Title', year=year, yeartag=yeartag)
        self.run_add()
        song = Song.objects.get()
        self.assertEquals(song.year, year)

    ###
    ### Actual tests follow
    ###

    def test_add_single_vbr_mp3(self):
        """
        Tests adding a single VBR mp3 to our library
        """
        self.mp3_mode_test('vbr')

    def test_add_single_cbr_mp3(self):
        """
        Tests adding a single CBR mp3 to our library
        """
        self.mp3_mode_test('cbr')

    def test_add_single_abr_mp3(self):
        """
        Tests adding a single ABR mp3 to our library
        """
        self.mp3_mode_test('abr')

    def test_add_mp3_simple_tag_check(self):
        """
        Adds a single fully-tagged track and check that the resulting database
        objects are all populated properly
        """
        self.add_mp3(artist='Artist', title='Title', album='Album',
            year=1970, tracknum=1)
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.year, 1970)
        self.assertEqual(album.artist.name, 'Artist')

        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.year, 1970)
        self.assertEqual(song.tracknum, 1)
        self.assertEqual(song.album.name, 'Album')
        self.assertEqual(song.artist.name, 'Artist')

    def test_add_mp3_total_track_tag_check(self):
        """
        Adds a single track to check for the alternate tracknum format
        where the maximum track count is included in the tag.
        """
        self.add_mp3(artist='Artist', title='Title', tracknum=1,
            maxtracks=5)
        self.run_add()

        song = Song.objects.get()
        self.assertEqual(song.tracknum, 1)

    def test_add_mp3_id3v23(self):
        """
        Adds a single track using ID3v2.3 encoding, rather than ID3v2.4.  The
        main thing we're checking here is for the year (whose tag changed between
        those two versions), but we'll be checking basically everything anyway.
        """
        self.add_mp3(artist='Artist', title='Title', album='Album',
            year=1970, tracknum=1, save_as_v23=True)
        self.run_add()
        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.year, 1970)
        self.assertEqual(song.tracknum, 1)
        self.assertEqual(song.album.name, 'Album')
        self.assertEqual(song.artist.name, 'Artist')

    def test_add_mp3_alternate_year_tdrl(self):
        """
        Adds a single track using the specific year tag TDRL, and verify
        that the year is populated properly.
        """
        self.mp3_year_test(1970, 'TDRL')

    def test_add_mp3_alternate_year_tdrc(self):
        """
        Adds a single track using the specific year tag TDRC, and verify
        that the year is populated properly.
        """
        self.mp3_year_test(1970, 'TDRC')

    def test_add_mp3_empty_track_tag(self):
        """
        Adds a single track with an empty tracknum field.  Note that
        mutagen refuses to write an actually-empty string to a tag,
        so we're using a space instead.  The important part is just
        that it's a value that fails when passed to int()
        """
        self.add_mp3(artist='Artist', title='Title', tracknum=' ')
        self.run_add()
        self.assertEqual(Song.objects.all().count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.tracknum, 0)

    def test_add_mp3_empty_year_tag(self):
        """
        Adds a single track with an empty year field.  Mutagen refuses to
        write out invalid tags, so we've just constructed one to pass in.
        This technically also tests an empty tracknum field, making the
        previous test unnecessary, but whatever, we'll do both.
        """
        self.add_mp3(basefile='invalid-tags.mp3', apply_tags=False)
        self.run_add()
        self.assertEqual(Song.objects.all().count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.year, 0)
        self.assertEqual(song.tracknum, 0)

    def test_add_mp3s_different_artist_case(self):
        """
        Adds two tracks by the same artist, but with different capitalization
        on the artist name.  Which version of the artist name gets stored is
        basically just dependent on whatever the app sees first.  I'm tempted
        to have it compare when it sees alternate cases and use the one with
        the most uppercase, but I think I'll just leave that to manual editing.
        """
        self.add_mp3(artist='Artist Name', title='Title 1', filename='song1.mp3')
        self.add_mp3(artist='artist name', title='Title 2', filename='song2.mp3')
        self.run_add()
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Artist.objects.all().count(), 2)
        # Note the mixed-case in the query, just checking that too.
        artist = Artist.objects.get(name='artist Name')
        self.assertEqual(artist.name.lower(), 'artist name')

    def test_add_mp3_artist_prefix(self):
        """
        Adds a single track with an artist name "The Artist" to check for
        proper prefix handling.
        """
        self.add_mp3(artist='The Artist', title='Title')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_add_mp3_no_album(self):
        """
        Adds an mp3 without an album to check that it's properly sorted
        into a 'Non-Album Tracks' album.
        """
        self.add_mp3(artist='Artist', title='Title')
        self.run_add()

        album_title = App.non_album_format_str % ('Artist')
        album = Album.objects.get()
        self.assertEqual(album.name, album_title)

    def test_add_mp3_two_song_album(self):
        """
        Adds two mp3s which should be in the same album.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album', filename='1-title_1.mp3')
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album', filename='2-title_2.mp3')
        self.run_add()

        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.artist.name, 'Artist')
        self.assertEqual(album.song_set.count(), 2)

    def test_add_mp3_two_alternating_prefix(self):
        """
        Add one mp3 with the artist name "The Artist"
        and then a second with the artist name "Artist".
        Both should be associated with the same base
        Artist name.
        """
        self.add_mp3(artist='The Artist', title='Title 1',
            album='Album 1', filename='album_1.mp3')
        self.run_add()
        self.add_mp3(artist='Artist', title='Title 2',
            album='Album 2', filename='album_2.mp3')
        self.run_add()

        for artist in Artist.objects.all():
            if artist.name != 'Various':
                self.assertEqual(artist.name, 'Artist')
                self.assertEqual(artist.prefix, 'The')
        for song in Song.objects.all():
            self.assertEqual(song.artist.name, 'Artist')

    def test_add_mp3_two_alternating_prefix_reverse(self):
        """
        Add one mp3 with the artist name "Artist" and
        then a second one with the artist name "The Artist".
        The artist record should be updated to have a
        prefix.
        """
        self.add_mp3(artist='Artist', title='Title 1',
            album='Album 1', filename='album_1.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        self.add_mp3(artist='The Artist', title='Title 2',
            album='Album 2', filename='album_2.mp3')
        self.run_add()

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_add_various_artists_album(self):
        """
        Test adding a various-artists album.
        """
        tracks = [
            ('1-title_1.mp3', 'Artist 1', 'Title 1', 1),
            ('2-title_2.mp3', 'Artist 2', 'Title 2', 2),
        ]
        for (filename, artist, title, tracknum) in tracks:
            self.add_mp3(artist=artist, title=title, album='Album',
                tracknum=tracknum, filename=filename)
        self.run_add()

        # First check that we have three total artists, and that
        # they're what we expect
        self.assertEqual(Artist.objects.all().count(), 3)
        va = Artist.objects.get(name='Various')
        self.assertEqual(va.name, 'Various')
        a1 = Artist.objects.get(name='Artist 1')
        self.assertEqual(a1.name, 'Artist 1')
        a2 = Artist.objects.get(name='Artist 2')
        self.assertEqual(a2.name, 'Artist 2')

        # Now check that there's just one album and that IT is
        # how we expect.
        self.assertEqual(Album.objects.all().count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.artist.name, 'Various')
        self.assertEqual(album.song_set.count(), 2)

        # Aaand check the individual songs
        for (filename, artist, title, tracknum) in tracks:
            song = Song.objects.get(filename=filename)
            self.assertEqual(song.title, title)
            self.assertEqual(song.artist.name, artist)
            self.assertEqual(song.album.name, 'Album')
            self.assertEqual(song.album.artist.name, 'Various')
            self.assertEqual(song.tracknum, tracknum)

    def test_add_va_album_and_normal_album(self):
        """
        Create a Various Artists album, and at the same time another
        album belonging to one of the artists on the VA comp.
        """
        tracks = [
            ('Various', '1-title_1.mp3', 'Artist 1', 'Title 1', 1),
            ('Various', '2-title_2.mp3', 'Artist 2', 'Title 2', 2),
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 1', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # First check that we have three total artists, and that
        # they're what we expect
        self.assertEqual(Artist.objects.all().count(), 3)
        va = Artist.objects.get(name='Various')
        self.assertEqual(va.name, 'Various')
        self.assertEqual(va.album_set.count(), 1)
        a1 = Artist.objects.get(name='Artist 1')
        self.assertEqual(a1.name, 'Artist 1')
        self.assertEqual(a1.album_set.count(), 1)
        a2 = Artist.objects.get(name='Artist 2')
        self.assertEqual(a2.name, 'Artist 2')
        self.assertEqual(a2.album_set.count(), 0)

        # Now check for two albums
        self.assertEqual(Album.objects.all().count(), 2)
        various = Album.objects.get(name='Various')
        self.assertEqual(various.name, 'Various')
        self.assertEqual(various.artist.name, 'Various')
        self.assertEqual(various.song_set.count(), 2)
        single = Album.objects.get(name='Album')
        self.assertEqual(single.name, 'Album')
        self.assertEqual(single.artist.name, 'Artist 1')
        self.assertEqual(single.song_set.count(), 2)

        # Now check the individual album tracks
        for song in various.song_set.all():
            self.assertNotEqual(song.artist.name, 'Various')
            self.assertEqual(song.album.name, 'Various')
            self.assertEqual(song.album.artist.name, 'Various')
        for song in single.song_set.all():
            self.assertEqual(song.artist.name, 'Artist 1')
            self.assertEqual(song.album.name, 'Album')
            self.assertEqual(song.album.artist.name, 'Artist 1')

    def test_add_normal_track_to_normal_album(self):
        """
        Create a single-artist album and then add another track to the
        album (by the same artist).
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 1', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Just verify that the album is Artist 1
        album = Album.objects.get(name='Album')
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.artist.name, 'Artist 1')

        # Now add the new track
        self.add_mp3(path='Album', filename='3-third.mp3',
            artist='Artist 1', title='Third', tracknum=3,
            album='Album')
        self.run_add()

        # Verify that we only have one album, and that it's still Artist 1
        self.assertEqual(Album.objects.all().count(), 1)
        album = Album.objects.get(name='Album')
        self.assertEqual(album.song_set.count(), 3)
        self.assertEqual(album.artist.name, 'Artist 1')

    def test_add_va_track_to_va_album(self):
        """
        Create a various-artist album and then add another track to the
        album.
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 2', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Just verify that the album is Various
        album = Album.objects.get(name='Album')
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.artist.name, 'Various')

        # Now add the new track
        self.add_mp3(path='Album', filename='3-third.mp3',
            artist='Artist 3', title='Third', tracknum=3,
            album='Album')
        self.run_add()

        # Verify that we only have one album, and that it's still VA
        self.assertEqual(Album.objects.all().count(), 1)
        album = Album.objects.get(name='Album')
        self.assertEqual(album.song_set.count(), 3)
        self.assertEqual(album.artist.name, 'Various')

    def test_add_va_track_to_non_va_album(self):
        """
        Create a regular single-artist album and then add a track to the
        album which turns it into a Various Artists album.
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 1', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Just verify that the album is Artist 1 quick
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        album = Album.objects.get(name='Album')
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.artist.name, 'Artist 1')

        # Now add the new track
        self.add_mp3(path='Album', filename='3-third.mp3',
            artist='Artist 2', title='Third', tracknum=3,
            album='Album')
        self.run_add()

        # Verify that we only have one album, and that it's changed
        self.assertEqual(Album.objects.all().count(), 1)
        album = Album.objects.get(name='Album')
        self.assertEqual(album.song_set.count(), 3)
        self.assertEqual(album.artist.name, 'Various')

    def test_add_two_regular_albums_with_same_album_name(self):
        """
        Test behavior when two regular albums are added with the same
        album name.  This is a subpar situation and may result in
        problems down the line, but for now the expected behavior
        is that there will be a single regular album containing tracks
        from both directories.
        """
        tracks = [
            ('al1', 'Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('al1', 'Album', '2-second.mp3', 'Artist 1', 'Second', 2),
            ('al2', 'Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('al2', 'Album', '2-second.mp3', 'Artist 1', 'Second', 2),
        ]
        for (path, album, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=album)
        self.run_add()

        # Some simple checks
        self.assertEqual(Song.objects.all().count(), 4)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.song_set.count(), 4)
        for song in Song.objects.all():
            self.assertEqual(song.album.name, 'Album')
            self.assertEqual(song.album.artist.name, 'Artist 1')
            self.assertEqual(song.artist.name, 'Artist 1')

    def test_add_two_va_albums_with_same_album_name(self):
        """
        Test behavior when two V/A albums are added with the same
        album name.  This is a subpar situation and may result in
        problems down the line, but for now the expected behavior
        is that there will be a single V/A album containing tracks
        from both directories.
        """
        tracks = [
            ('va1', 'Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('va1', 'Album', '2-second.mp3', 'Artist 2', 'Second', 2),
            ('va2', 'Album', '1-first.mp3', 'Artist 3', 'First', 1),
            ('va2', 'Album', '2-second.mp3', 'Artist 4', 'Second', 2),
        ]
        for (path, album, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=album)
        self.run_add()

        # Some simple checks
        self.assertEqual(Song.objects.all().count(), 4)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 5)
        album = Album.objects.get()
        self.assertEqual(album.song_set.count(), 4)
        for song in Song.objects.all():
            self.assertEqual(song.album.name, 'Album')
            self.assertEqual(song.album.artist.name, 'Various')

class BasicUpdateAsAddTests(BasicAddTests):
    """
    This is a bit of nonsense.  Basically, all tests for add() should be
    repeated for update(), since add() is technically a subset of update().
    Rather than rewriting everything, we're just subclassing and
    overriding the `run_add()` method so that all calls to `run_add()`
    end up doing an update instead.
    """

    def run_add(self):
        """
        Runs an `update` operation on our library while pretending to be
        `add`, and checks for errors.
        """
        return self.assertNoErrors(App.update())

class BasicUpdateTests(ExordiumTests):
    """
    Tests for the update procedure - this time, tests specifically related
    to the update() call, rather than fiddling around.
    """

    def test_basic_update(self):
        """
        Test a simple track update to the title.
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'Title')

        # Now make some changes.
        self.update_mp3(filename='song.mp3', title='New Title')
        self.run_update()

        # Now the real verifications
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.title, 'New Title')

    def test_basic_album_update(self):
        """
        Test a simple track update in which the album name changes
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.album.name, 'Album')

        # Now make some changes
        self.update_mp3(filename='song.mp3', album='New Album')
        self.run_update()

        # Now the real verification
        self.assertEqual(Album.objects.all().count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Artist')
        self.assertEqual(album.name, 'New Album')
        self.assertEqual(album.song_set.count(), 1)
        self.assertEqual(Song.objects.all().count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.album.name, 'New Album')

    def test_basic_artist_update(self):
        """
        Test a simple track update in which the artist name changes
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')

        # Now make some changes
        self.update_mp3(filename='song.mp3', artist='New Artist')
        self.run_update()

        # Now the real verification
        self.assertEqual(Artist.objects.all().count(), 2)
        artist = Artist.objects.get(name='New Artist')
        self.assertEqual(artist.name, 'New Artist')
        self.assertEqual(Album.objects.all().count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'New Artist')
        self.assertEqual(album.name, 'Album')
        self.assertEqual(album.song_set.count(), 1)
        self.assertEqual(Song.objects.all().count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.artist.name, 'New Artist')

    def test_basic_artist_and_album_update(self):
        """
        Test a simple track update in which the artist and album name changes
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album')
        self.run_add()

        # Quick verification
        song = Song.objects.get()
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.album.name, 'Album')

        # Now make some changes
        self.update_mp3(filename='song.mp3', artist='New Artist', album='New Album')
        self.run_update()

        # Now the real verification
        self.assertEqual(Artist.objects.all().count(), 2)
        artist = Artist.objects.get(name='New Artist')
        self.assertEqual(artist.name, 'New Artist')
        self.assertEqual(Album.objects.all().count(), 1)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'New Artist')
        self.assertEqual(album.name, 'New Album')
        self.assertEqual(album.song_set.count(), 1)
        self.assertEqual(Song.objects.all().count(), 1)
        song = Song.objects.get()
        self.assertEqual(song.title, 'Title')
        self.assertEqual(song.artist.name, 'New Artist')
        self.assertEqual(song.album.name, 'New Album')

    def test_update_song_delete(self):
        """
        Test a track deletion (also ensures that album+artist records get cleared out)
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.all().count(), 1)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)

        # Do the delete
        self.delete_file('song.mp3')
        self.run_update()

        # Now the real checks
        self.assertEqual(Song.objects.all().count(), 0)
        self.assertEqual(Album.objects.all().count(), 0)
        self.assertEqual(Artist.objects.all().count(), 1)

    def test_update_song_delete_keep_album(self):
        """
        Test a track deletion with an album which stays in place
        """
        self.add_mp3(filename='song.mp3', artist='Artist', title='Title',
            album = 'Album')
        self.add_mp3(filename='song2.mp3', artist='Artist', title='Title 2',
            album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)

        # Do the delete
        self.delete_file('song2.mp3')
        self.run_update()

        # Now the real checks
        self.assertEqual(Song.objects.all().count(), 1)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.song_set.count(), 1)
        song = album.song_set.get()
        self.assertEqual(song.title, 'Title')

    def test_update_song_move(self):
        """
        Test a move of a file from one location to another other.
        """
        self.add_mp3(path='starting', filename='song.mp3',
            artist='Artist', title='Title', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.all().count(), 1)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)

        artist = Artist.objects.get(name='Artist')
        artist_pk = artist.pk
        artist_name = artist.name

        album = Album.objects.get()
        album_pk = album.pk
        album_name = album.name

        song = Song.objects.get()
        song_pk = song.pk
        song_album = song.album.name
        song_artist = song.artist.name
        song_title = song.title
        song_year = song.year
        song_tracknum = song.tracknum
        song_filetype = song.filetype
        song_bitrate = song.bitrate
        song_mode = song.mode
        song_size = song.size
        song_length = song.length
        song_time_added = song.time_added
        song_time_updated = song.time_updated
        song_sha256sum = song.sha256sum

        # Move the file
        self.move_file(song.filename, 'ending')
        self.run_update()

        # Check the data
        self.assertEqual(Song.objects.all().count(), 1)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)

        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist_pk, artist.pk)
        self.assertEqual(artist_name, artist.name)

        album = Album.objects.get()
        self.assertEqual(album_pk, album.pk)
        self.assertEqual(album_name, album.name)

        song = Song.objects.get()
        self.assertEqual('ending/song.mp3', song.filename)
        self.assertEqual(song_pk, song.pk)
        self.assertEqual(song_album, song.album.name)
        self.assertEqual(song_artist, song.artist.name)
        self.assertEqual(song_title, song.title)
        self.assertEqual(song_year, song.year)
        self.assertEqual(song_tracknum, song.tracknum)
        self.assertEqual(song_filetype, song.filetype)
        self.assertEqual(song_bitrate, song.bitrate)
        self.assertEqual(song_mode, song.mode)
        self.assertEqual(song_size, song.size)
        self.assertEqual(song_length, song.length)
        self.assertEqual(song_time_added, song.time_added)
        self.assertEqual(song_time_updated, song.time_updated)
        self.assertEqual(song_sha256sum, song.sha256sum)

    def test_update_change_prefix(self):
        """
        Test an update of a file which adds a previously-unknown
        prefix to an artist.
        """
        self.add_mp3(filename='1-first.mp3',
            artist='Artist', title='Title 1', album = 'Album')
        self.add_mp3(filename='2-second.mp3',
            artist='Artist', title='Title 1', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, '')

        # Do the update
        self.update_mp3('2-second.mp3', artist='The Artist')
        self.run_update()

        # Check
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

    def test_update_no_change_prefix(self):
        """
        Test an update of a file which removes the artist prefix on the
        tags - initial prefix on artist should remain in place.
        """
        self.add_mp3(filename='1-first.mp3',
            artist='The Artist', title='Title 1', album = 'Album')
        self.add_mp3(filename='2-second.mp3',
            artist='The Artist', title='Title 1', album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')

        # Do the update
        self.update_mp3('2-second.mp3', artist='Artist')
        self.run_update()

        # Check
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        artist = Artist.objects.get(name='Artist')
        self.assertEqual(artist.name, 'Artist')
        self.assertEqual(artist.prefix, 'The')
        song = Song.objects.get(filename='2-second.mp3')
        self.assertEqual(song.artist.name, 'Artist')
        self.assertEqual(song.artist.prefix, 'The')

    def test_update_single_artist_to_various(self):
        """
        Tests an update which should transform a single-artist album
        to a Various album.
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 1', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Some quick sanity checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Artist 1')

        # Now make the change
        self.update_mp3('Album/2-second.mp3', artist='Artist 2')
        self.run_update()

        # Now checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 3)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Various')

    def test_update_various_artist_to_single(self):
        """
        Tests an update which should transform a various-artist album
        to a single-artist album.
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 2', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Some quick sanity checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 3)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Various')

        # Now make the change
        self.update_mp3('Album/2-second.mp3', artist='Artist 1')
        self.run_update()

        # Now checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Artist 1')

    def test_update_various_artist_to_various(self):
        """
        Tests an update which should keep a various-artist album
        as a various-artist album (though with a different artist)
        """
        tracks = [
            ('Album', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album', '2-second.mp3', 'Artist 2', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Some quick sanity checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 3)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Various')

        # Now make the change
        self.update_mp3('Album/2-second.mp3', artist='Artist 3')
        self.run_update()

        # Now checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 3)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Various')
        for artist in Artist.objects.all():
            self.assertNotEqual(artist.name, 'Artist 2')

    def test_update_song_delete_from_various_to_single(self):
        """
        Test a track deletion with an album which will go from being
        Various Artsits to a single-artist
        """
        self.add_mp3(filename='song.mp3', artist='Artist 1', title='Title',
            album = 'Album')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Album')
        self.add_mp3(filename='song3.mp3', artist='Artist 2', title='Title 3',
            album = 'Album')
        self.run_add()

        # Quick verification
        self.assertEqual(Song.objects.all().count(), 3)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 3)
        album = Album.objects.get()
        self.assertEqual(album.artist.name, 'Various')

        # Now delete
        self.delete_file('song3.mp3')
        self.run_update()

        # Now verify
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.song_set.count(), 2)
        self.assertEqual(album.artist.name, 'Artist 1')
        for song in album.song_set.all():
            self.assertEqual(song.artist.name, 'Artist 1')

    def test_update_entire_album_name_pk_stays_the_same(self):
        """
        Test an update of the album name from all tracks in an
        album.  The primary key of the album should remain the
        same.
        """
        self.add_mp3(filename='song.mp3', artist='Artist 1', title='Title',
            album = 'Old Album')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Old Album')
        self.run_add()

        # Some quick checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.name, 'Old Album')
        album_pk = album.pk

        # Now do the updates
        self.update_mp3('song.mp3', album='New Album')
        self.update_mp3('song2.mp3', album='New Album')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.name, 'New Album')
        self.assertEqual(album.pk, album_pk)

    def test_update_split_into_two_albums(self):
        """
        Test an update where a previously-single album is now split into
        two separate albums.
        """
        self.add_mp3(filename='song1.mp3', artist='Artist 1', title='Title 1',
            album = 'Album 1')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Album 1')
        self.run_add()

        # Some quick checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)

        # Now updates
        self.update_mp3('song1.mp3', album='Album 2')
        self.update_mp3('song2.mp3', album='Album 3')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 2)
        self.assertEqual(Artist.objects.all().count(), 2)
        a2 = Album.objects.get(name='Album 2')
        self.assertEqual(a2.name, 'Album 2')
        self.assertEqual(a2.song_set.count(), 1)
        self.assertEqual(a2.song_set.get().title, 'Title 1')
        a3 = Album.objects.get(name='Album 3')
        self.assertEqual(a3.name, 'Album 3')
        self.assertEqual(a3.song_set.count(), 1)
        self.assertEqual(a3.song_set.get().title, 'Title 2')

    def test_update_split_into_extra_album(self):
        """
        Test an update where an album with two tracks is split into two
        albums (but the first track remains in the first album).  In
        this case we expect the "Album 1" album to remain itself (same pk).
        """
        self.add_mp3(filename='song1.mp3', artist='Artist 1', title='Title 1',
            album = 'Album 1')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Album 1')
        self.run_add()

        # Some quick checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        album = Album.objects.get()
        album_pk = album.pk

        # Now updates
        self.update_mp3('song2.mp3', album='Album 2')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 2)
        self.assertEqual(Artist.objects.all().count(), 2)
        a1 = Album.objects.get(name='Album 1')
        self.assertEqual(a1.name, 'Album 1')
        self.assertEqual(a1.song_set.count(), 1)
        self.assertEqual(a1.song_set.get().title, 'Title 1')
        a2 = Album.objects.get(name='Album 2')
        self.assertEqual(a1.pk, album_pk)
        self.assertEqual(a2.name, 'Album 2')
        self.assertEqual(a2.song_set.count(), 1)
        self.assertEqual(a2.song_set.get().title, 'Title 2')

    def test_update_split_into_extra_album_2(self):
        """
        Test an update where an album with two tracks is split into two
        albums (but the first track remains in the first album), this
        time with a reversed album title to trigger two different scenarios
        in the update code.  In this case, "Album 1" will get renamed "Album 2"
        and then a new "Album 1" album will be created.  This is subpar, but
        this should only ever happen accidentally anyway, so we'll just Not
        Care.
        """
        self.add_mp3(filename='song1.mp3', artist='Artist 1', title='Title 1',
            album = 'Album 2')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Album 2')
        self.run_add()

        # Some quick checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)

        # Now updates
        self.update_mp3('song2.mp3', album='Album 1')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 2)
        self.assertEqual(Artist.objects.all().count(), 2)
        a2 = Album.objects.get(name='Album 2')
        self.assertEqual(a2.name, 'Album 2')
        self.assertEqual(a2.song_set.count(), 1)
        self.assertEqual(a2.song_set.get().title, 'Title 1')
        a1 = Album.objects.get(name='Album 1')
        self.assertEqual(a1.name, 'Album 1')
        self.assertEqual(a1.song_set.count(), 1)
        self.assertEqual(a1.song_set.get().title, 'Title 2')

    def test_update_two_albums_different_artists_become_one_artist(self):
        """
        Tests having two albums by two different artists, one of which then
        gets updated to have the same artist as the first.
        """
        tracks = [
            ('Album 1', '1-first.mp3', 'Artist 1', 'First', 1),
            ('Album 1', '2-second.mp3', 'Artist 1', 'Second', 2),
            ('Album 2', '1-first.mp3', 'Artist 2', 'First', 1),
            ('Album 2', '2-second.mp3', 'Artist 2', 'Second', 2),
        ]
        for (path, filename, artist, title, tracknum) in tracks:
            self.add_mp3(path=path, filename=filename, artist=artist,
                title=title, tracknum=tracknum, album=path)
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.all().count(), 4)
        self.assertEqual(Album.objects.all().count(), 2)
        self.assertEqual(Artist.objects.all().count(), 3)

        # Now the update
        self.update_mp3('Album 2/1-first.mp3', artist='Artist 1')
        self.update_mp3('Album 2/2-second.mp3', artist='Artist 1')
        self.run_update()

        # Checks
        self.assertEqual(Song.objects.all().count(), 4)
        self.assertEqual(Album.objects.all().count(), 2)
        self.assertEqual(Artist.objects.all().count(), 2)
        artist = Artist.objects.get(name='Artist 1')
        self.assertEqual(artist.album_set.count(), 2)
        album = Album.objects.get(name='Album 2')
        self.assertEqual(album.artist.name, 'Artist 1')

    def test_update_both_new_and_updated_files_to_single_album(self):
        """
        Test a situation where we have a directory with two songs (each
        in their own album), one gets updated to be an album with the
        first, and also a new file is added which is a third track on
        the album.
        """
        self.add_mp3(filename='song1.mp3', artist='Artist 1', title='Title 1',
            album = 'Album 1')
        self.add_mp3(filename='song2.mp3', artist='Artist 1', title='Title 2',
            album = 'Album 2')
        self.run_add()

        # Quick checks
        self.assertEqual(Song.objects.all().count(), 2)
        self.assertEqual(Album.objects.all().count(), 2)
        self.assertEqual(Artist.objects.all().count(), 2)
        album = Album.objects.get(name='Album 1')
        album_pk = album.pk

        # Now the updates
        self.update_mp3('song2.mp3', album='Album 1')
        self.add_mp3(filename='song3.mp3', artist='Artist 1', title='Title 3',
            album = 'Album 1')
        self.run_update()

        # Now the real checks
        self.assertEqual(Song.objects.all().count(), 3)
        self.assertEqual(Album.objects.all().count(), 1)
        self.assertEqual(Artist.objects.all().count(), 2)
        album = Album.objects.get()
        self.assertEqual(album.pk, album_pk)
        self.assertEqual(album.song_set.count(), 3)
        for filename in ['song1.mp3', 'song2.mp3', 'song3.mp3']:
            song = Song.objects.get(filename=filename)
            self.assertEqual(song.album.name, 'Album 1')
            self.assertEqual(song.artist.name, 'Artist 1')