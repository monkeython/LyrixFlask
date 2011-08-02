from flask import Flask, request, flash, abort, redirect, url_for
from werkzeug.contrib.cache import SimpleCache, GAEMemcachedCache
from musixmatch.ws import artist, album, track, matcher
import musixmatch.api
import os

__author__ = "Luca De Vitis <luca@monkeython.com>"
__version__ = '0.1'
__copyright__ = "2011, %s " % __author__
__license__ = """
   Copyright (C) %s

      This program is free software: you can redistribute it and/or modify
      it under the terms of the GNU General Public License as published by
      the Free Software Foundation, either version 3 of the License, or
      (at your option) any later version.

      This program is distributed in the hope that it will be useful,
      but WITHOUT ANY WARRANTY; without even the implied warranty of
      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
      GNU General Public License for more details.

      You should have received a copy of the GNU General Public License
      .along with this program.  If not, see <http://www.gnu.org/licenses/>.
""" % __copyright__
__doc__ = """
:version: %s
:author: %s
:organization: Monkeython
:contact: http://www.monkeython.com
:copyright: %s
""" % (__version__, __author__, __license__)
__docformat__ = 'restructuredtext en'
__classifiers__ = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Operating System :: OS Independent',
    'Topic :: Internet :: WWW/HTTP' ]

NAME = os.paht.splitext(os.path.basename(__file__))[0]
CACHE = SimpleCache()
DEBUG = False
TESTING = False
PROPAGATE_EXCEPTIONS = False
PRESERVE_CONTEXT_ON_EXCEPTION = False
SECRET_KEY = ''
SESSION_COOKIE_NAME = NAME
PERMANENT_SESSION_LIFETIME = 0
USE_X_SENDFILE = False
LOGGER_NAME = NAME
SERVER_NAME = 'localhost'
MAX_CONTENT_LENGTH = 0

class TestingSettings(Default):
    TESTING = True

class DebugSettings(Testing):
    DEBUG = True

class AppSpotSettings(Default):
    CACHE = GAEMemcachedCache(300, NAME.lower())

application = Flask(__name__)
application.config.from_object(__name__)
_settings = os.environ['%s_SETTINGS' % NAME.upper()]
if os.path.isfile(_settings):
    application.config.from_pyfile(_settings)
else:
    application.config.from_object(_settings)

def _cache(item_label, item_list):
    """Cache each item in list."""
    id_label = item_label + '_id'
    mbid_label = item_label + '_mbid'
    echonest_id_label = item_label + '_echonest_id'
    items = {}
    for item in item_list:
        key = '/%s/%s' % (item_label, item[id_label])
        items[key] = item
        musicbrainz_id = item.get(mbid_label, None)
        if musicbrainz_id:
            items['/musicbrainz/%s/%s' % (item_label, musicbrainz_id)] = key
        # echonest_id = item.get(echonest_id_label, None)
        # if echonest_id:
        #     items['/echonest/%s/%s' % (item_label, echonest_id)] = key
    application.config.get('CACHE').set_many(items)

def api_method(*keys):
    """Decorator function to wrap a musixmatch web service api method. It maps
    Flask rule arguments to musixmatch.api.Method keywords arguments and cache
    results::

    >>> import musixmatch.ws
    >>> 
    >>> @application.route(...)
    >>> @api_method()
    >>> musixmatch.ws.track.chart.get
    >>> 
    >>> @application.route(...)
    >>> @api_method('artist_id')
    >>> musixmatch.ws.artist.get
    """
    def decorator(webservice_api):
        api_method = musixmatch.api.Method(str(webservice_api))
        api_method_name = api_method.__name__
        @wraps(api_method)
        def wrapper(*values):
            arguments = keys and dict(zip(keys,values)) or request.values
            path = url_for(api_method_name, **arguments).split('?')[0]
            body = cache.get(path)
            if not body:
                message = api_method(**arguments)
                if not message.status:
                    flash(message.status, 'error')
                    abort(message.status)
                body = message['body']

                label, value = body.items()[0]
                if label.endswith('_list'):
                    item_label = label[:-5]
                    item_list = value
                else:
                    item_label = label
                    item_list = [value]
                _cache(item_label, item_list)

            return body
        wrapper.__name__ = api_method.__name__
        return wraper
    return decorator

@application.route('/artist/<artist_id>')
@api_method('artist_id')
artist.get

@application.route('/artist/<artist_id>/albums', defaults={'page': 1})
@application.route('/artist/<artist_id>/albums/page/<int:page>')
@api_method('artist_id', 'page')
artist.albums.get

@application.route('/artist/chart', defaults={'country': 'us', 'page': 1})
@application.route('/<string(length=2):country>/artist/chart/page/<int:page>')
@api_method('country', 'page')
artist.chart.get

@application.route('/artist/search')
@api_method()
artist.search

@application.route('/album/<album_id>')
@api_method('album_id')
album.get

@application.route('/album/<album_id>/tracks', defaults={'page': 1})
@application.route('/album/<album_id>/tracks/page/<int:page>')
@api_method('album_id', 'page')
album.tracks.get

@application.route('/track/<track_id>')
@api_method('track_id')
track.get

@application.route('/track/<track_id>/lyrics')
@api_method('track_id')
track.lyrics.get

@application.route('/track/<track_id>/lyrics', methods=['POST'])
@api_method('track_id')
track.lyrics.post

@application.route('/track/<track_id>/lyrics/feedback', methods=['POST'])
@api_method('track_id')
track.lyrics.feedback.post

@application.route('/track/search')
@api_method()
track.search

@application.route('/track/chart', defaults={'country': 'us', 'page': 1})
@application.route('/<string(length=2):country>/track/chart/page/<int:page>')
@api_method('country', 'page')
track.chart.get

@application.route('/track/matcher')
@api_method()
matcher.track.get

# _rule = '/<any("musicbrainz", "echonest"):other>'\
#         '/<any("artist", "album", "track"):item>' \
#         '/<identifier>'
_musicbrainz = \
    '/musicbrainz/<any("artist", "album", "track"):item_label>/<identifier>'
@application.route(_musicbrainz, default={'subpath': ''})
@application.route(_musicbrainz + '/<path:subpath>')
def musicbrainz(item_label, identifier, subpath):
    item_path = application.config.get('CACHE').get(request.path)
    if not item_path:
        api_method = musixmatch.api.Method(item_label + '.get')
        message = api_method(**{item_label + '_mbid': identifier})
        if not message.status:
            flash(message.status, 'error')
            abort(message.status)
        _cache(item_label, [message['body'][item_label]])
        item_id = message['body'][item_label][item_label + '_id']
        item_path = '/%s/%s' % (item_label, item_id)
    redirect(subpath and '%s/%s' % (item_path, subpath) or item_path, 307)
