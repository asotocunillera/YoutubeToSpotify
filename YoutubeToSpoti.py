from decouple import config
from apiclient.discovery import build
import spotipy
import pandas as pd
class YoutubetoSpoti(object):

    def __init__(self, secret_keys):
        #Youtube keys
        self.YT_API_KEY = secret_keys[0]
        #Spotify keys
        self.SP_USERNAME = secret_keys[1]
        self.SP_CLIENT_ID = secret_keys[2]
        self.SP_CLIENT_SECRET = secret_keys[3]
        self.SP_SCOPE = secret_keys[4]

        self.MAX_RESULTS = 50
        #name of youtube songs usually has words and characters not included in Spotify
        self.REPLACEMENTS = ['(', ')', '[', ']', '/',' ft', ' feat', ' vs', ',', 'official', ' audio',
        'lyrics', 'lyric', 'video', ' hd ', 'edit', 'music', '. ']

        try:
            print('[INFO] Initilising Youtube Client...')
            self.yt_client = build('youtube', 'v3', developerKey=self.YT_API_KEY)
            print('[INFO] Initialised!')
        except:
            print('[ERROR] Not posible to initialize Youtube Client')

        try:
            print('[INFO] Initilising Spotify Client...')
            auth = spotipy.util.prompt_for_user_token(
                username = self.SP_USERNAME,
                scope = self.SP_SCOPE,
                client_id=self.SP_CLIENT_ID,
                client_secret=self.SP_CLIENT_SECRET,
                redirect_uri='http://localhost/'
                )
            self.sp_client = spotipy.Spotify(auth = auth)
            print('[INFO] Initialised!')
        except:
            print('[ERROR] Not posible to initialize Spotify Client')


    def yt_playlist_tracks(self, playlist_ID):
        playlist_response = self.yt_client.playlistItems().list(
            part = 'snippet',
            playlistId = playlist_ID,
            maxResults = self.MAX_RESULTS
        ).execute()
        playlist = playlist_response['items']
        videos = [(video['snippet']['title']).lower() for video in playlist]
        titles = []
        print("[INFO] Filtering name of youtube songs...")
        for video in videos:
            for replacement in self.REPLACEMENTS:
                if replacement in video:
                    video = video.replace(replacement,'')
            title = video.rsplit(' - ')[0] + ' ' + video.rsplit(' - ')[1]
            titles.append(title)
        return titles

    def yt_channel_tracks(self, channel_username):
        channels_response = self.yt_client.channels().list(
            part='contentDetails', 
            forUsername = channel_username).execute()
        print(f'[INFO] Looking for uploads in {channel_username}...')
        channel_uploads = channels_response['items'][-1]['contentDetails']['relatedPlaylists']['uploads']
        titles = yt_playlist_tracks(channel_uploads)
        return titles

    def sp_search(self, titles):
        print('[INFO] Searching filtered titles in Spotify...')
        sp_found_IDs = []
        database_found = []
        database_not_found = []
        for title in titles:
            sp_search = self.sp_client.search(
                title,
                limit = 1,
                offset=0,
                type='track',
                market=None
            )
            if sp_search['tracks']['total'] != 0: #Song found
                track_ID = sp_search['tracks']['items'][0]['id']
                sp_found_IDs.append(track_ID)
                print(f'[INFO] Track found: {title}')
                track = self.sp_client.track(track_ID)
                track_artists = ', '.join([i['name'] for i in track['album']['artists']])
                track = track_artists + ' - ' + track['name']
                database_found.append((title, track))
            else: #Song not found, reducing name lenght and trying again
                aux_title = title
                while(len(aux_title)>=15):
                    aux_title = aux_title.rsplit(' ',1)[0]
                    sp_search = self.sp_client.search(
                        aux_title,
                        limit = 1,
                        offset=0,
                        type='track',
                        market=None
                    )
                    if sp_search ['tracks']['total'] != 0: #Song found
                        track_ID = sp_search['tracks']['items'][0]['id']
                        sp_found_IDs.append(track_ID)
                        print(f'[INFO] Track found: {title}')
                        track = self.sp_client.track(track_ID)
                        track_artists = ', '.join([i['name'] for i in track['album']['artists']])
                        track = track_artists + ' - ' + track['name']
                        database_found.append((title, track))
                        break
                if sp_search ['tracks']['total'] == 0: #Song not found
                    print(f'[WARNING] Track not found {title}')
                    database_not_found.append(title)

        return sp_found_IDs, database_found, database_not_found

    def addto_sp_playlist(self, sp_tracks_found_ID):
        tracks_to_add = []
        tracks = []

        with open('SpotifyTracks.txt','r') as f:
            playlist_titles = f.read().splitlines()
        playlist_titles = playlist_titles[1:]

        for track_ID in sp_tracks_found:
            track = self.sp_client.track(track_ID)
            track_artists = ', '.join([i['name'] for i in track['album']['artists']])
            track = track_artists + ' - ' + track['name']

            if track not in playlist_titles:
                print(f'[INFO] Adding track: {track}')
                tracks_to_add.append(track_ID)
                tracks.append(track)
            else:
                print(f'[INFO] Track already in playlist: {track}')

# def main():

YT_API_KEY = config('YT_API_KEY')
SP_USERNAME = config('SP_USERNAME')
SP_CLIENT_ID = config('SP_CLIENT_ID')
SP_CLIENT_SECRET = config('SP_CLIENT_SECRET')
SP_SCOPE = config('SP_SCOPE')

YT_PLAYLIST_ID = config('YT_PLAYLIST_ID')

SECRET_KEYS = [YT_API_KEY, SP_USERNAME, SP_CLIENT_ID, SP_CLIENT_SECRET, SP_SCOPE]
myYoutubetoSpoti = YoutubetoSpoti(SECRET_KEYS)
titles = myYoutubetoSpoti.yt_playlist_tracks(YT_PLAYLIST_ID)
(sp_found_IDs, database_found, database_not_found) = myYoutubetoSpoti.sp_search(titles)
