from django.shortcuts import render, get_object_or_404
from django.views import generic
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.urls import reverse
from django.template import loader, Context
from django.http import HttpResponse, StreamingHttpResponse, Http404

from django_tables2 import RequestConfig

from dynamic_preferences.registries import global_preferences_registry

from .models import Artist, Album, Song, App, AlbumArt
from .tables import ArtistTable, AlbumTable, SongTableWithAlbum, SongTableNoAlbum, SongTableWithAlbumNoTracknum, SongTableNoAlbumNoTracknum

# Create your views here.

class TitleListView(generic.ListView):
    """
    Simple extension to django.views.generic.ListView which
    allows us to set exordium_title as part of our object,
    which will then get added to the context and passed to our
    template.
    """

    exordium_title = 'Sub-Page'

    def get_context_data(self, **kwargs):
        context = super(TitleListView, self).get_context_data(**kwargs)
        context['exordium_title'] = self.exordium_title
        return context

class TitleDetailView(generic.DetailView):
    """
    Simple extension to django.views.generic.DetailView which
    allows us to set exordium_title as part of our object,
    which will then get added to the context and passed to our
    template.
    """

    exordium_title = 'Sub-Page'

    def get_context_data(self, **kwargs):
        context = super(TitleDetailView, self).get_context_data(**kwargs)
        context['exordium_title'] = self.exordium_title
        return context

class TitleTemplateView(generic.TemplateView):
    """
    Simple extension to django.views.generic.TemplateView which
    allows us to set exordium_title as part of our object,
    which will then get added to the context and passed to our
    template.
    """

    exordium_title = 'Sub-Page'

    def get_context_data(self, **kwargs):
        context = super(TitleTemplateView, self).get_context_data(**kwargs)
        context['exordium_title'] = self.exordium_title
        return context

class IndexView(TitleTemplateView):
    template_name = 'exordium/index.html'
    exordium_title = 'Exordium Main Page'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        albums = list(Album.objects.all().order_by('-time_added')[:20])
        table = AlbumTable(albums)
        RequestConfig(self.request).configure(table)
        context['album_list'] = table
        return context

class SearchView(TitleTemplateView):
    template_name = 'exordium/search.html'
    exordium_title = 'Search Results'

    def get_context_data(self, **kwargs):
        context = super(SearchView, self).get_context_data(**kwargs)

        # Grab and sanitize our search string a bit
        search = self.request.GET['q']
        if "\n" in search:
            search = search.split("\n")[0]
        if "\r" in search:
            search = search.split("\r")[0]
        if len(search) > 80:
            search = search[:80]

        # Now do some searching
        show_artists = False
        show_albums = False
        show_songs = False

        artists = Artist.objects.filter(name__icontains=search).order_by('name')
        if artists.count() > 0:
            show_artists = True
            table = ArtistTable(artists, prefix='artist-')
            RequestConfig(self.request).configure(table)
            context['artist_results'] = table

        albums = Album.objects.filter(name__icontains=search).order_by('name')
        if albums.count() > 0:
            show_albums = True
            table = AlbumTable(albums, prefix='album-')
            RequestConfig(self.request).configure(table)
            context['album_results'] = table

        songs = Song.objects.filter(title__icontains=search).order_by('title')
        if songs.count() > 0:
            show_songs = True
            table = SongTableWithAlbumNoTracknum(songs, prefix='song-')
            RequestConfig(self.request).configure(table)
            context['song_results'] = table

        context['found_results'] = (show_artists or show_albums or show_songs)

        context['q'] = search
        return context

class ArtistView(TitleDetailView):
    model = Artist
    template_name = 'exordium/artist.html'

    def get_context_data(self, **kwargs):
        context = super(ArtistView, self).get_context_data(**kwargs)
        albums = Album.objects.filter(
            Q(artist=self.object) |
            Q(song__artist=self.object) |
            Q(song__group=self.object) |
            Q(song__conductor=self.object) |
            Q(song__composer=self.object)
        ).distinct().order_by('artist__various', 'miscellaneous', 'name')
        table = AlbumTable(albums)
        RequestConfig(self.request).configure(table)
        context['albums'] = table
        context['exordium_title'] = 'Albums by %s' % (self.object)
        return context

class AlbumView(TitleDetailView):
    model = Album
    template_name = 'exordium/album.html'

    def get_context_data(self, **kwargs):
        context = super(AlbumView, self).get_context_data(**kwargs)
        songs = Song.objects.filter(album=self.object).order_by('tracknum')
        (groups, conductors, composers) = self.object.get_secondary_artists_tuple()
        data = []
        for song in songs:
            song.set_album_secondary_artist_counts(num_groups=len(groups),
                num_conductors=len(conductors), num_composers=len(composers))
            data.append(song)
        if self.object.miscellaneous:
            table = SongTableNoAlbumNoTracknum(data)
        else:
            table = SongTableNoAlbum(data)
        RequestConfig(self.request).configure(table)
        context['songs'] = table
        context['exordium_title'] = '%s / %s' % (self.object.artist, self.object)
        context['groups'] = groups
        context['conductors'] = conductors
        context['composers'] = composers
        return context

class BrowseArtistView(TitleListView):
    model = Artist
    template_name = 'exordium/browse.html'
    exordium_title = 'Browsing Artists'

    def get_context_data(self, **kwargs):
        context = super(BrowseArtistView, self).get_context_data(**kwargs)
        artists = Artist.objects.all().order_by('name')
        table = ArtistTable(artists)
        RequestConfig(self.request).configure(table)
        context['table'] = table
        return context

class BrowseAlbumView(TitleListView):
    model = Album
    template_name = 'exordium/browse.html'
    exordium_title = 'Browsing Albums'

    def get_context_data(self, **kwargs):
        context = super(BrowseAlbumView, self).get_context_data(**kwargs)
        albums = Album.objects.all().order_by('artist__name','name')
        table = AlbumTable(albums)
        RequestConfig(self.request).configure(table)
        context['table'] = table
        return context

@method_decorator(staff_member_required, name='dispatch')
class LibraryView(TitleTemplateView):
    template_name = 'exordium/library.html'
    exordium_title = 'Library Management'

    def get_context_data(self, **kwargs):
        context = super(LibraryView, self).get_context_data(**kwargs)
        prefs = global_preferences_registry.manager()
        context['base_path'] = prefs['exordium__base_path']
        context['media_url'] = prefs['exordium__media_url']
        context['count_artists'] = Artist.objects.count()
        context['count_albums'] = Album.objects.count()
        context['count_songs'] = Song.objects.count()
        return context

class LibraryActionView(generic.View):

    exordium_title = 'Library Action'
    update_func = staticmethod(App.add)

    def get(self, request, *args, **kwargs):
        """
        We support GET
        """
        return StreamingHttpResponse((line for line in self.update_generator()))

    def update_generator(self):
        template_page = loader.get_template('exordium/library_update.html')
        template_line = loader.get_template('exordium/library_update_line.html')
        context = Context({
            'request': self.request,
            'exordium_title': self.exordium_title,
        })
        page = template_page.render(context)
        for line in page.split("\n"):
            if line == '@__LIBRARY_UPDATE_AREA__@':
                for (status, line) in self.update_func():
                    yield template_line.render(Context({
                        'status': status,
                        'line': line,
                    }))
            else:
                yield line

@method_decorator(staff_member_required, name='dispatch')
class LibraryAddView(LibraryActionView):

    exordium_title = 'Add Music to Library'
    update_func = staticmethod(App.add)

@method_decorator(staff_member_required, name='dispatch')
class LibraryUpdateView(LibraryActionView):

    exordium_title = 'Update/Clean Libraries'
    update_func = staticmethod(App.update)

class OriginalAlbumArtView(generic.View):
    """
    Class to handle showing the original album art for an
    album.  Just a weird passthrough to the filesystem.
    Not Django-approved!
    """

    def get(self, request, *args, **kwargs):
        """
        The main request!
        """

        # We don't actually care about the extension
        extension = kwargs['extension']

        # Grab the album.  Send a 404 if it doesn't exist.
        try:
            albumid = int(kwargs['albumid'])
        except ValueError:
            albumid = -1
        album = get_object_or_404(Album, pk=albumid)

        filename = album.get_original_art_filename()
        if filename:
            with open(filename, 'rb') as df:
                return HttpResponse(df.read(), content_type=album.art_mime)
        else:
            raise Http404('Album art not found for album "%s / %s"' % (album.artist, album))

class AlbumArtView(generic.View):
    """
    Class to handle showing album art.
    """

    def get(self, request, *args, **kwargs):
        """
        The main request!
        """

        # What size have we been requested
        size = kwargs['size']
        if size not in [t[0] for t in AlbumArt.SIZE_CHOICES]:
            # TODO: this should do something more intelligent
            raise Http404('Invalid size choice: %s' % (size))

        # Grab the album.  Send a 404 if it doesn't exist.
        try:
            albumid = int(kwargs['albumid'])
        except ValueError:
            albumid = -1
        album = get_object_or_404(Album, pk=albumid)

        # Try to grab the album art and display it
        art = AlbumArt.get_or_create(album, size)
        if art:
            return HttpResponse(art.image, content_type='image/jpeg')
        else:
            raise Http404('Album art not found for album "%s / %s"' % (album.artist, album))
