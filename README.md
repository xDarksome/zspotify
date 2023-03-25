# zspotify

zspotify is a Spotify downloader that enables users to find and download songs.


## Requirements

- Python 3.9 or greater
- ffmpeg

> :warning: ffmpeg should be installed from your package manager of choice on Linux or by
downloading the binaries from [ffmpeg.org](https://ffmpeg.org) and placing them in your %PATH% in Windows.


## Installation (pip)

```bash
pip install git+https://github.com/jsavargas/zspotify
```


## Installation (Docker)

WIP


## Usage

```
usage: zspotify [-h] [-ap] [-sp] [-ls] [-pl PLAYLIST] [-tr TRACK] [-al ALBUM] [-ar ARTIST] [-ep EPISODE]
                [-fs FULL_SHOW] [-cd CONFIG_DIR] [--archive ARCHIVE] [-d DOWNLOAD_DIR] [-md MUSIC_DIR]
                [-pd EPISODES_DIR] [-v] [-af {mp3,ogg}] [--album-in-filename] [--antiban-time ANTIBAN_TIME]
                [--antiban-album ANTIBAN_ALBUM] [--limit LIMIT] [-f] [-ns] [-s] [-cf CREDENTIALS_FILE]
                [-bd BULK_DOWNLOAD]
                [search]

positional arguments:
  search                Searches for a track, album, artist or playlist or download by url

options:
  -h, --help            show this help message and exit
  -ap, --all-playlists  Downloads all saved playlist from your library
  -sp, --select-playlists
                        Downloads a saved playlist from your library
  -ls, --liked-songs    Downloads your liked songs
  -pl PLAYLIST, --playlist PLAYLIST
                        Download playlist by id or url
  -tr TRACK, --track TRACK
                        Downloads a track from their id or url
  -al ALBUM, --album ALBUM
                        Downloads an album from their id or url
  -ar ARTIST, --artist ARTIST
                        Downloads an artist from their id or url
  -ep EPISODE, --episode EPISODE
                        Downloads a episode from their id or url
  -fs FULL_SHOW, --full-show FULL_SHOW
                        Downloads all show episodes from id or url
  -cd CONFIG_DIR, --config-dir CONFIG_DIR
                        Folder to save the config files
  --archive ARCHIVE     File to save the downloaded files
  -d DOWNLOAD_DIR, --download-dir DOWNLOAD_DIR
                        Folder to save the downloaded files
  -md MUSIC_DIR, --music-dir MUSIC_DIR
                        Folder to save the downloaded music files
  -pd EPISODES_DIR, --episodes-dir EPISODES_DIR
                        Folder to save the downloaded episodes files
  -v, --version         Shows the current version of ZSpotify
  -af {mp3,ogg}, --audio-format {mp3,ogg}
                        Audio format to download the tracks
  --album-in-filename   Adds the album name to the filename
  --antiban-time ANTIBAN_TIME
                        Time to wait between downloads to avoid Ban
  --antiban-album ANTIBAN_ALBUM
                        Time to wait between album downloads to avoid Ban
  --limit LIMIT         limit
  -f, --force-premium   Force premium account
  -ns, --not-skip-existing
                        If flag setted NOT Skip existing already downloaded tracks
  -s, --skip-downloaded
                        Skip already downloaded songs if exist in archive even it is doesn't exist in the filesystem
  -cf CREDENTIALS_FILE, --credentials-file CREDENTIALS_FILE
                        File to save the credentials
  -bd BULK_DOWNLOAD, --bulk-download BULK_DOWNLOAD
                        Bulk download from file with urls
```


## Changelog

[View Changelog Here](https://github.com/jsavargas/zspotify/CHANGELOG.md)


## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

- [GitHub](https://github.com/jsavargas/zspotify) of this repository.
- [DockerHub](https://hub.docker.com/r/jsavargas/zspotify) of this repository.


## Acknowledgements

- [Footsiefat](https://github.com/Footsiefat) for original zspotify implementation
