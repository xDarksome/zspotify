from zspotify import zspotify_api

from appdirs import user_config_dir
from getpass import getpass
from mutagen import id3
from pathlib import Path
from threading import Thread
from tqdm import tqdm

import argparse
import datetime
import json
import os
import platform
import requests
import sys
import time


__version__ = "2.0.0_alpha"
__author__ = [{"name": "Jonathan Salinas Vargas", "github": "https://github.com/jsavargas"},
              {"name": "Yuriy Kovrigin", "github": "https://github.com/Bionded"}]

_ANTI_BAN_WAIT_TIME = os.environ.get('ANTI_BAN_WAIT_TIME', 5)
_ANTI_BAN_WAIT_TIME_ALBUMS = os.environ.get('ANTI_BAN_WAIT_TIME_ALBUMS', 30)
_LIMIT_RESULTS = os.environ.get('LIMIT_RESULTS', 10)


class archive:

    def __init__(self, file):
        self.file = file
        self.data = self.load()

    def load(self):
        if self.file.exists():
            with open(self.file, "r") as f:
                try:
                    return json.load(f)
                except Exception as e:
                    print("Error loading archive: {}".format(e))
                    return {}
        return {}

    def save(self):
        with open(self.file, "w") as f:
            json.dump(self.data, f, indent=4)

    def add(self, track_id, artist=None, track_name=None, fullpath=None,
            audio_type=None, timestamp=None, save=True):
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.data[track_id] = {"artist": artist,
                               "track_name": track_name,
                               "audio_type": audio_type,
                               "fullpath": str(fullpath),
                               "timestamp": timestamp
                               }
        print("Added to archive: {} - {}".format(artist, track_name))
        if save:
            self.save()

    def get(self, track_id):
        return self.data.get(track_id)

    def remove(self, track_id):
        self.data.pop(track_id)
        self.save()

    def exists(self, track_id):
        return track_id in self.data

    def get_all(self):
        return self.data

    def get_ids_from_old_archive(self, old_archive_file):
        archive = []
        folder = old_archive_file.parent
        if old_archive_file.exists():
            with open(old_archive_file, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    song = line.split("\t")
                    try:
                        track_id = song[0]
                        timestamp = song[1]
                        artist = song[2]
                        track_name = song[3]
                        fullpath = None
                        if Path(folder, song[4]).exists():
                            fullpath = str(Path(folder, song[4]))

                        archive.append({"track_id": track_id,
                                        "track_artist": artist,
                                        "track_name": track_name,
                                        "timestamp": timestamp,
                                        "fullpath": fullpath})
                    except Exception as e:
                        print("Error parsing line: {}".format(line))
                        print(e)
            return archive
        return None

    def delete_not_existing(self):
        for track_id in self.data:
            if not self.data[track_id]["fullpath"].exists():
                self.remove(track_id)
        self.save()


# UTILS
class zspotify:

    def __init__(self):
        self.SANITIZE_CHARS = ["\\", "/", ":", "*", "?", "'", "<", ">", '"']
        self.SEPARATORS = [",", ";"]
        self.args = self.parse_args()
        self.zs_api = zspotify_api(
            sanitize=self.SANITIZE_CHARS,
            config_dir=self.args.config_dir,
            music_format=self.args.audio_format,
            force_premium=self.args.force_premium,
            anti_ban_wait_time=self.args.antiban_time,
            credentials=self.args.credentials_file,
            limit=self.args.limit)

        self.config_dir = self.args.config_dir
        self.download_dir = Path.home() / "Music"
        if self.args.download_dir:
            self.download_dir = Path.home() / self.args.download_dir

        self.music_dir = Path(self.download_dir, "ZSpotify Music")
        self.episodes_dir = Path(self.download_dir, "ZSpotify Podcasts")

        if self.args.music_dir:
            self.music_dir = Path.home() / self.args.music_dir
        if self.args.episodes_dir:
            self.episodes_dir = Path.home() / self.args.episodes_dir

        self.album_in_filename = self.args.album_in_filename
        self.antiban_album_time = self.args.antiban_album
        self.not_skip_existing = self.args.not_skip_existing
        self.skip_downloaded = self.args.skip_downloaded
        self.archive_file = Path(self.args.config_dir, self.args.archive)
        self.archive = archive(self.archive_file)

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("search",
                            help="Searches for a track, album, artist or playlist or download by url",
                            const=None, nargs="?")
        parser.add_argument("-ap", "--all-playlists",
                            help="Downloads all saved playlist from your library",
                            action="store_true")
        parser.add_argument("-sp", "--select-playlists",
                            help="Downloads a saved playlist from your library",
                            action="store_true")
        parser.add_argument("-ls", "--liked-songs",
                            help="Downloads your liked songs",
                            action="store_true")
        parser.add_argument("-pl", "--playlist",
                            help="Download playlist by id or url")
        parser.add_argument("-tr", "--track",
                            help="Downloads a track from their id or url")
        parser.add_argument("-al", "--album",
                            help="Downloads an album from their id or url")
        parser.add_argument("-ar", "--artist",
                            help="Downloads an artist from their id or url")
        parser.add_argument("-ep", "--episode",
                            help="Downloads a episode from their id or url")
        parser.add_argument("-fs", "--full-show",
                            help="Downloads all show episodes from id or url")
        parser.add_argument("-cd", "--config-dir",
                            help="Folder to save the config files",
                            default=user_config_dir("ZSpotify"))
        parser.add_argument("--archive",
                            help="File to save the downloaded files",
                            default="archive.json")
        parser.add_argument("-d", "--download-dir",
                            help="Folder to save the downloaded files")
        parser.add_argument("-md", "--music-dir",
                            help="Folder to save the downloaded music files")
        parser.add_argument("-pd", "--episodes-dir",
                            help="Folder to save the downloaded episodes files")
        parser.add_argument("-v", "--version",
                            help="Shows the current version of ZSpotify",
                            action="store_true")
        parser.add_argument("-af", "--audio-format",
                            help="Audio format to download the tracks",
                            default="mp3", choices=["mp3", "ogg"])
        parser.add_argument("--album-in-filename",
                            help="Adds the album name to the filename",
                            action="store_true", default=False)
        parser.add_argument("--antiban-time",
                            help="Time to wait between downloads to avoid Ban",
                            default=_ANTI_BAN_WAIT_TIME, type=int)
        parser.add_argument("--antiban-album",
                            help="Time to wait between album downloads to avoid Ban",
                            default=_ANTI_BAN_WAIT_TIME_ALBUMS, type=int)
        parser.add_argument("--limit",
                            help="limit",
                            default=_LIMIT_RESULTS, type=int)
        parser.add_argument("-f", "--force-premium",
                            help="Force premium account",
                            action="store_true", default=False)
        parser.add_argument("-ns", "--not-skip-existing",
                            help="If flag setted NOT Skip existing already downloaded tracks",
                            action="store_false", default=True)
        parser.add_argument("-s", "--skip-downloaded",
                            help="Skip already downloaded songs if exist in archive",
                            action="store_true", default=False)
        parser.add_argument("-cf", "--credentials-file",
                            help="File to save the credentials",
                            default=Path(user_config_dir("ZSpotify"), "credentials.json"))
        parser.add_argument("-bd", "--bulk-download",
                            help="Bulk download from file with urls")

        return parser.parse_args()

    def splash(self):
        """Displays splash screen"""
        print(
            """
    ███████ ███████ ██████   ██████  ████████ ██ ███████ ██    ██
       ███  ██      ██   ██ ██    ██    ██    ██ ██       ██  ██
      ███   ███████ ██████  ██    ██    ██    ██ █████     ████
     ███         ██ ██      ██    ██    ██    ██ ██         ██
    ███████ ███████ ██       ██████     ██    ██ ██         ██
        """
        )
        print(f"version: {__version__}")

    def split_input(self, selection):
        """Splits the input into a list"""
        # if one from separator in selections
        for sep in self.SEPARATORS:
            if sep in selection:
                return selection.split(sep)
        return [selection]

    def clear(self):
        """Clear the console window"""
        if platform.system() == "Windows":
            os.system("cls")
        else:
            os.system("clear")

    def antiban_wait(self, seconds: int = 5):
        """ Pause between albums for a set number of seconds """
        for i in range(seconds)[::-1]:
            print("\rWait for Next Download in %d second(s)..." % (i + 1), end="")
            time.sleep(1)

    def sanitize_data(self, value):
        """Returns given string with problematic removed"""
        for i in self.SANITIZE_CHARS:
            value = value.replace(i, "")
        return value.replace("|", "-")

    def login(self):
        """Login to Spotify"""
        logged_in = self.zs_api.login()
        if logged_in:
            return True
        print("Login to Spotify")
        username = input("Username: ")
        password = getpass()
        return self.zs_api.login(username, password)

    def set_audio_tags(self,
                       filename,
                       artists=None,
                       name=None,
                       album_name=None,
                       release_year=None,
                       disc_number=None,
                       track_number=None,
                       track_id_str=None,
                       album_artist=None,
                       image_url=None):
        """sets music_tag metadata using mutagen"""
        artist = artists

        if artist is not None and album_artist is None:
            album_artist = artist

        tags = id3.ID3(filename)
        if artist is not None:
            # TPE1 Lead Artist/Performer/Soloist/Group
            tags["TPE1"] = id3.TPE1(
                encoding=3, text=artist
            )
        if name is not None:
            # TIT2 Title/songname/content description
            tags["TIT2"] = id3.TIT2(
                encoding=3, text=name
            )
        if album_name is not None:
            # TALB Album/Movie/Show title
            tags["TALB"] = id3.TALB(encoding=3, text=album_name)
        if release_year is not None:
            # TDRC Recording time
            tags["TDRC"] = id3.TDRC(encoding=3, text=release_year)
            # TDOR Original release time
            tags["TDOR"] = id3.TDOR(encoding=3, text=release_year)
        if disc_number is not None:
            # TPOS Part of a set
            tags["TPOS"] = id3.TPOS(encoding=3, text=str(disc_number))
        if track_number is not None:
            # TRCK Track number/Position in set
            tags["TRCK"] = id3.TRCK(
                encoding=3, text=str(track_number)
            )
        if track_id_str is not None:
            # COMM User comment
            tags["COMM"] = id3.COMM(
                encoding=3, lang="eng", text="https://open.spotify.com/track/" + track_id_str
            )
        if album_artist is not None:
            # TPE2 Band/orchestra/accompaniment
            tags["TPE2"] = id3.TPE2(
                encoding=3, text=album_artist
            )
        if image_url is not None:
            albumart = requests.get(image_url).content if image_url else None
            if albumart:
                # APIC Attached (or linked) Picture.
                tags["APIC"] = id3.APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="0",
                    data=albumart,
                )
        # TCON Genre - TODO
        tags.save()

    # ARCHIVE
    def archive_migration(self):
        """Migrates the old archive to the new one"""
        for path in [self.config_dir, self.download_dir, self.music_dir, self.episodes_dir]:
            tracks = self.archive.get_ids_from_old_archive(Path(path, ".song_archive"))
            if tracks:
                print("Found old archive, migrating to new one...")
                for track in tracks:
                    if self.archive.exists(track['track_id']):
                        print(f"Skipping {track['track_name']} - Already in archive")
                        continue
                    self.archive.add(track['track_id'],
                                     artist = track['track_artist'],
                                     track_name = track['track_name'],
                                     fullpath = track['fullpath'],
                                     timestamp = track['timestamp'],
                                     audio_type = "music",
                                     save = False)
                self.archive.save()
            try:
                os.remove(Path(path, ".song_archive"))
            except OSError:
                pass
            print(f"Migration complete from file: {str(Path(path, '.song_archive'))}")

    # DOWNLOADERS
    def download_track(self, track_id, path=None, caller=None):
        if self.args.skip_downloaded and self.archive.exists(track_id):
            print(f"Skipping {track_id} - Already Downloaded")
            return True
        track = self.zs_api.get_audio_info(track_id)
        if track['is_playable'] == False:
            print(f"Skipping {track['audio_name']} - Not Available")
            return True

        if caller == "album":
            basepath = path or self.music_dir
            filename = self.sanitize_data(f"{track['audio_number']}. {track['audio_name']}.{self.args.audio_format}")
            if self.album_in_filename:
                filename = self.sanitize_data(f"{track['album']} {track['audio_number']}. {track['audio_name']}.{self.args.audio_format}")
            fullpath = Path(basepath, filename)
        elif caller == "playlist":
            basepath = path or self.music_dir
            filename = Path(f"{track['artist_name']} - {track['audio_name']}.{self.args.audio_format}")
            if self.album_in_filename:
                filename = self.sanitize_data(f"{track['artist_name']} - {track['album']} - {track['audio_name']}.{self.args.audio_format}")
            fullpath = Path(basepath, filename)
        elif caller == "show":
            basepath = path or self.episodes_dir
            filename = self.sanitize_data(f"{track['audio_number']}. {track['audio_name']}.{self.args.audio_format}")
            fullpath = Path(basepath, filename)
        elif caller == "episode":
            basepath = path or self.episodes_dir
            filename = self.sanitize_data(f"{track['artist_name']} - {track['audio_number']}. {track['audio_name']}.{self.args.audio_format}")
            fullpath = Path(basepath, filename)
        else:
            basepath = path or self.music_dir
            filename = self.sanitize_data(f"{track['artist_name']} - {track['audio_name']}.{self.args.audio_format}")
            fullpath = Path(basepath, filename)

        if self.not_skip_existing and fullpath.exists():
            print(f"Skipping {filename} - Already downloaded")
            return True
        downloader = Thread(target=self.zs_api.download_audio, args=(track_id, fullpath, True))
        downloader.start()
        while not self.zs_api.progress:
            time.sleep(0.1)
        with tqdm(
                desc=filename,
                total=self.zs_api.progress['total'],
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
        ) as progress_bar:
            progress = self.zs_api.progress
            while progress:
                progress_bar.update(progress['downloaded'] - progress_bar.n)
                time.sleep(0.1)
                progress = self.zs_api.progress
            progress_bar.update(progress_bar.total - progress_bar.n)
        print(f"Converting {filename}")
        self.archive.add(track_id,
                         artist=track['artist_name'],
                         track_name=track['audio_name'],
                         fullpath=fullpath,
                         audio_type="music")
        downloader.join()
        print(f"Set audiotags {filename}")
        self.set_audio_tags(fullpath,
                            artists=track['artist_name'],
                            name=track['audio_name'],
                            album_name=track['album_name'],
                            release_year=track['release_year'],
                            disc_number=track['disc_number'],
                            track_number=track['audio_number'],
                            track_id_str=track['scraped_song_id'],
                            image_url=track['image_url'])
        print(f"Finished downloading {filename}")

    def download_playlist(self, playlist_id):
        playlist = self.zs_api.get_playlist_info(playlist_id)
        if not playlist:
            print("Playlist not found")
            return False
        songs = self.zs_api.get_playlist_songs(playlist_id)
        if not songs:
            print("Playlist is empty")
            return False
        print(f"Downloading {playlist['name']} playlist")
        basepath = Path(self.music_dir, self.sanitize_data(playlist['name']))
        for song in songs:
            self.download_track(song['id'], basepath, "playlist")
        print(f"Finished downloading {playlist['name']} playlist")

    def download_all_user_playlists(self):
        playlists = self.zs_api.get_all_user_playlists()
        if not playlists:
            print("No playlists found")
            return False
        for playlist in playlists['playlists']:
            self.download_playlist(playlist['id'])
            self.antiban_wait(self.antiban_album_time)
        print("Finished downloading all user playlists")

    def download_select_user_playlists(self):
        playlists = self.zs_api.get_all_user_playlists()
        if not playlists:
            print("No playlists found")
            return False
        for i, playlist in enumerate(playlists['playlists']):
            print(f"    {i + 1}. {playlist['name']}")

        print('''
        > SELECT A PLAYLIST BY ID.
        > SELECT A RANGE BY ADDING A DASH BETWEEN BOTH ID's.
          For example, typing 10 to get one playlist or 10-20 to get
          every playlist from 10-20 (inclusive).
        > SELECT A MULTIPLE PLAYLISTS BY ADDING A COMMA BETWEEN IDs.
          For example, typing 10,11,20 will select playlists
          10, 11 and 20 respectively.
          Typing 1,11-20 will select playlists 1 and 11-20 (inclusive).
        ''')
        user_input = input("ID(s): ")

        # Parse user input
        user_formatted_input = set()
        for part in user_input.split(','):
            x = part.split('-')
            user_formatted_input.update(range(int(x[0]), int(x[-1])+1))
        sorted(user_formatted_input)

        # Clean user input
        invalid_ids = []
        playlist_ids = []
        for track_id in user_formatted_input:
            if track_id > len(playlists['playlists']) or track_id < 1:
                invalid_ids.append(track_id)
            else:
                playlist_ids.append(playlists['playlists'][track_id - 1]['id'])
        if invalid_ids:
            print(f'{invalid_ids} do not exist, downloading the rest')

        for playlist in playlist_ids:
            self.download_playlist(playlist)
            self.antiban_wait(self.antiban_album_time)
        print("Finished downloading selected playlists")

    def download_album(self, album_id):
        album = self.zs_api.get_album_info(album_id)
        if not album:
            print("Album not found")
            return False
        songs = self.zs_api.get_album_songs(album_id)
        if not songs:
            print("Album is empty")
            return False
        print(f"Downloading {album['artists']} - {album['name']} album")
        basepath = Path(self.music_dir, self.sanitize_data(album['artists']),
                                self.sanitize_data(f"{album['release_date']} - {album['name']}"))
        for song in songs:
            self.download_track(song['id'], basepath, "album")
        print(f"Finished downloading {album['artists']} - {album['name']} album")
        return True

    def download_artist(self, artist_id):
        artist = self.zs_api.get_artist_info(artist_id)
        if not artist:
            print("Artist not found")
            return False
        albums = self.zs_api.get_artist_albums(artist_id)
        if not albums:
            print("Artist has no albums")
            return False
        for album in albums:
            self.download_album(album['id'])
            self.antiban_wait(self.antiban_album_time)
        print(f"Finished downloading {artist['name']} artist")
        return True

    def download_liked_songs(self):
        songs = self.zs_api.get_liked_tracks()
        if not songs:
            print("No liked songs found")
            return False
        print("Downloading liked songs")
        basepath = Path(self.music_dir, "Liked Songs")
        for song in songs:
            self.download_track(song['id'], basepath, "liked_songs")
        print("Finished downloading liked songs")
        return True

    def download_by_url(self, url):
        parsed_url = self.zs_api.parse_url(url)
        if parsed_url['track']:
            ret = self.download_track(parsed_url['track'])
        elif parsed_url['playlist']:
            ret = self.download_playlist(parsed_url['playlist'])
        elif parsed_url['album']:
            ret = self.download_album(parsed_url['album'])
        elif parsed_url['artist']:
            ret = self.download_artist(parsed_url['artist'])
        elif parsed_url['episode']:
            ret = self.download_episode(parsed_url['episode'])
        elif parsed_url['show']:
            ret = self.download_all_show_episodes(parsed_url['show'])
        else:
            print("Invalid URL")
            return False
        return ret

    def download_episode(self, episode_id, caller="episode"):
        if self.args.skip_downloaded and self.archive.exists(episode_id):
            print(f"Skipping {episode_id} - Already Downloaded")
            return True

        episode = self.zs_api.get_episode_info(episode_id)
        if not episode:
            print("Episode not found")
            return False
        print(f"Downloading {episode['audio_name']} episode")

        if episode['is_playable']==False:
            print(f"Skipping {episode['audio_name']} - Not Available")
            return True
        basepath = self.episodes_dir
        filename = self.sanitize_data(f"{episode['show_name']} - {episode['audio_name']}.{self.args.audio_format}")

        if caller == "show":
            basepath = Path(self.episodes_dir, self.sanitize_data(episode['show_name']))
            filename = self.sanitize_data(f"{episode['audio_name']}.{self.args.audio_format}")

        fullpath = Path(basepath, filename)

        if self.not_skip_existing and fullpath.exists():
            print(f"Skipping {filename} - Already downloaded")
            return True

        # self.zs_api.download_audio(episode_id, fullpath, True)
        downloader = Thread(target=self.zs_api.download_audio, args=(episode_id, fullpath, True))
        downloader.start()
        while not self.zs_api.progress:
            time.sleep(0.1)
        with tqdm(
                desc=filename,
                total=self.zs_api.progress['total'],
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
        ) as progress_bar:
            progress = self.zs_api.progress
            while progress:
                progress_bar.update(progress['downloaded'] - progress_bar.n)
                time.sleep(0.1)
                progress = self.zs_api.progress
            progress_bar.update(progress_bar.total - progress_bar.n)
        print(f"Converting {episode['audio_name']} episode")
        downloader.join()
        self.archive.add(episode_id,
                         artist=episode['show_name'],
                         track_name=episode['audio_name'],
                         fullpath=fullpath,
                         audio_type="episode")
        print(f"Set audiotags {episode['audio_name']}")
        self.set_audio_tags(fullpath,
                            artists=episode['show_name'],
                            name=episode['audio_name'],
                            release_year=episode['release_year'],
                            track_id_str=episode_id,
                            image_url=episode['image_url'])
        print(f"Finished downloading {episode['audio_name']} episode")

    def download_all_show_episodes(self, show_id):
        show = self.zs_api.get_show_info(show_id)
        if not show:
            print("Show not found")
            return False
        episodes = self.zs_api.get_show_episodes(show_id)
        if not episodes:
            print("Show has no episodes")
            return False
        for episode in episodes:
            self.download_episode(episode['id'], "show")
        print(f"Finished downloading {show['name']} show")
        return True

    def search(self, query):
        # TODO: Add search by artist, album, playlist, etc.
        results = self.zs_api.search(query)
        if not results:
            print("No results found")
            return False
        print("Search results:")
        print("###TRACKS###")
        i = 0
        full_results = []
        for result in results['tracks']:
            print(f"{i}. {result['artists']} - {result['name']}")
            result['type'] = 'track'
            full_results.append(result)
            i += 1
        print("###ALBUMS###")
        for result in results['albums']:
            print(f"{i}. {result['artists']} - {result['name']}")
            result['type'] = 'album'
            full_results.append(result)
            i += 1
        print("###PLAYLISTS###")
        for result in results['playlists']:
            print(f"{i}. {result['name']}")
            result['type'] = 'playlist'
            full_results.append(result)
            i += 1
        print("###ARTISTS###")
        for result in results['artists']:
            print(f"{i}. {result['name']}")
            result['type'] = 'artist'
            full_results.append(result)
            i += 1
        print("")
        print("Enter the number of the item you want to download")
        print(f"allowed delimiters: {self.SEPARATORS}")
        print("Enter 'all' to download all items")
        print("Enter 'exit' to exit")
        selection = input(">>>")
        if selection == "exit":
            return False
        if selection == "all":
            for result in full_results:
                if result['type'] == 'track':
                    self.download_track(result['id'])
                elif result['type'] == 'album':
                    self.download_album(result['id'])
                elif result['type'] == 'playlist':
                    self.download_playlist(result['id'])
                elif result['type'] == 'artist':
                    self.download_artist(result['id'])
            return True
        for item in self.split_input(selection):
            if int(item) >= len(full_results):
                print("Invalid selection")
                return False
            result = full_results[int(item)]
            if result['type'] == 'track':
                self.download_track(result['id'])
            elif result['type'] == 'album':
                self.download_album(result['id'])
            elif result['type'] == 'playlist':
                self.download_playlist(result['id'])
            elif result['type'] == 'artist':
                self.download_artist(result['id'])
        return True

    def start(self):
        """Main client loop"""
        self.splash()
        while not self.login():
            print("Invalid credentials")

        if self.args.version:
            print(f"ZSpotify version: {__version__}")
            return

        self.archive_migration()
        if self.args.all_playlists:
            self.download_all_user_playlists()
        if self.args.select_playlists:
            self.download_select_user_playlists()
        if self.args.liked_songs:
            self.download_liked_songs()
        if self.args.playlist:
            for playlist in self.split_input(self.args.playlist):
                if "spotify.com" in self.args.playlist:
                    self.download_by_url(playlist)
                else:
                    self.download_playlist(playlist)
        if self.args.album:
            for album in self.split_input(self.args.album):
                if "spotify.com" in self.args.album:
                    self.download_by_url(album)
                else:
                    self.download_album(album)
        if self.args.artist:
            for artist in self.split_input(self.args.artist):
                if "spotify.com" in self.args.artist:
                    self.download_by_url(artist)
                else:
                    self.download_artist(artist)
        if self.args.track:
            for track in self.split_input(self.args.track):
                if "spotify.com" in self.args.track:
                    self.download_by_url(track)
                else:
                    self.download_track(track)
            print("All Done")
        if self.args.episode:
            for episode in self.split_input(self.args.episode):
                if "spotify.com" in self.args.episode:
                    self.download_by_url(episode)
                else:
                    self.download_episode(episode)
        if self.args.full_show:
            for show in self.split_input(self.args.full_show):
                if "spotify.com" in self.args.full_show:
                    self.download_by_url(show)
                else:
                    self.download_all_show_episodes(show)
        if self.args.search:
            for query in self.split_input(self.args.search):
                if "spotify.com" in query:
                    self.download_by_url(query)
                else:
                    self.search(query)
        if self.args.bulk_download:
            with open(self.args.bulk_download, "r") as file:
                for line in file:
                    for url in self.split_input(line.strip()):
                        self.download_by_url(url)
        elif len(sys.argv) <= 1:
            self.args.search = input("Search: ")
            if self.args.search:
                self.search(self.args.search)
            else:
                print("Invalid input")


if __name__ == "__main__":
    try:
        zs = zspotify()
        zs.start()
    except KeyboardInterrupt:
        print("Interrupted by user")
        sys.exit(0)
    except Exception as error:
        print(f"[!] ERROR {error} ")
