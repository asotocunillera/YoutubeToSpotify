from decouple import config
from apiclient.discovery import build
from openpyxl import load_workbook
import spotipy
import argparse
import pandas as pd

class YoutubetoSpoti(object):

    def __init__(self, secret_keys , MAX_RESULTS):
        #Youtube keys
        self.YT_API_KEY = secret_keys[0]
        #Spotify keys
        self.SP_USERNAME = secret_keys[1]
        self.SP_CLIENT_ID = secret_keys[2]
        self.SP_CLIENT_SECRET = secret_keys[3]
        self.SP_SCOPE = secret_keys[4]

        self.MAX_RESULTS = MAX_RESULTS
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
            try:
                title = ((video.rsplit('-')[0]).strip() + ' ' + (video.rsplit('-')[1]).strip()).strip()
            except:
                print(f'[WARNING] Seems not a song: {video}')
            titles.append(title)
        return titles

    def yt_channel_tracks(self, channel_username):
        channels_response = self.yt_client.channels().list(
            part='contentDetails', 
            forUsername = channel_username).execute()
        print(f'[INFO] Looking for uploads in {channel_username}...')
        channel_uploads = channels_response['items'][-1]['contentDetails']['relatedPlaylists']['uploads']
        titles = self.yt_playlist_tracks(channel_uploads)
        return titles

    def sp_search(self, titles):
        print('[INFO] Searching filtered titles in Spotify...')
        sp_found_IDs = []
        database_found = pd.DataFrame(columns= ['YOUTUBE', 'SPOTIFY'])
        database_not_found = pd.DataFrame(columns = ['YOUTUBE'])
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
                database_found=database_found.append(pd.DataFrame([[title, track]], columns = ['YOUTUBE', 'SPOTIFY']))
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
                        database_found=database_found.append(pd.DataFrame([[title, track]], columns = ['YOUTUBE', 'SPOTIFY']))
                        break
                if sp_search ['tracks']['total'] == 0: #Song not found
                    print(f'[WARNING] Track not found {title}')
                    database_not_found=database_not_found.append(title)
        return sp_found_IDs, database_found, database_not_found

    def add_to_sp_playlist(self, sp_found_IDs, SP_PLAYLIST_ID):
        self.sp_client.user_playlist_add_tracks(
            user=self.SP_USERNAME,
            playlist_id=SP_PLAYLIST_ID,
            tracks=sp_found_IDs,
            position=0
        )
        print(f'[INFO] Added {len(sp_found_IDs)} songs successfully!')

def get_args(info):
    parser = argparse.ArgumentParser(
        description='{desc}'.format(** info),
        epilog='{license}, {email}'.format(** info)
    )
    parser.add_argument('-o', '--option',
        required=True,
        help = "Choose between Playlist or Channel Uploads [p/c]"
    )
    parser.add_argument('-r' ,'--results',
        default=50,
        help='Max results to track [default = 50]'
    )
    return vars(parser.parse_args())

def main(args):

    YT_API_KEY = config('YT_API_KEY')
    SP_USERNAME = config('SP_USERNAME')
    SP_CLIENT_ID = config('SP_CLIENT_ID')
    SP_CLIENT_SECRET = config('SP_CLIENT_SECRET')
    SP_SCOPE = config('SP_SCOPE')

    SP_PLAYLIST_ID = config('SP_PLAYLIST_ID') 

    MAX_RESULTS = int(args['results'])

    book_name = 'Tracks.xlsx'
    book = load_workbook(book_name)
    writer = pd.ExcelWriter(book_name, engine ='openpyxl')
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)

    xlsx_database_found = pd.read_excel(writer, sheet_name='Found', engine='openpyxl')
    xlsx_database_not_found = pd.read_excel(writer, sheet_name='Not Found', engine='openpyxl')

    SECRET_KEYS = [YT_API_KEY, SP_USERNAME, SP_CLIENT_ID, SP_CLIENT_SECRET, SP_SCOPE]
    myYoutubetoSpoti = YoutubetoSpoti(SECRET_KEYS, MAX_RESULTS)
    titles = []

    if args['option'] == 'p': #Playlist METHOD
        #By default I choose my unique YT_PLAYLIST
        YT_PLAYLIST_ID = config('YT_PLAYLIST_ID') 
        titles = myYoutubetoSpoti.yt_playlist_tracks(YT_PLAYLIST_ID)
    else: #Channels Uploads
        channels = []
        while True:
            channel = input("Channel Username (q to exit): ")
            if channel == 'q':
                break
            channels.append(channel)
        for channel in channels:
            try:
                titles.extend(myYoutubetoSpoti.yt_channel_tracks(channel))
            except:
                print(f'[WARNING] Channel Username: {channel} not valid')

    titles = [title for title in titles if all([title not in xlsx_database_found['YOUTUBE'].unique(),title not in xlsx_database_not_found['YOUTUBE'].unique()])]
    if titles:
        (sp_found_IDs, sp_found_tracks, sp_not_found_tracks) = myYoutubetoSpoti.sp_search(titles)
        myYoutubetoSpoti.add_to_sp_playlist(sp_found_IDs, SP_PLAYLIST_ID)

        print('[INFO] Saving new songs in database...')
        xlsx_database_not_found = xlsx_database_not_found.append(sp_not_found_tracks, ignore_index=True)
        xlsx_database_found = xlsx_database_found.append(sp_found_tracks, ignore_index=True)
        xlsx_database_found.to_excel(writer, sheet_name='Found', index=False)
        xlsx_database_not_found.to_excel(writer, sheet_name='Not Found', index=False)
        writer.save()
        print('[INFO] Done!')
    else:
        print('[INFO] No Tracks to add!')

if __name__=='__main__':

    info =  {
        'name': 'YoutubeToSpoti',
        'desc': 'Save Youtube music (from a playlist or channel uploads) into a Spotify Playlist',
        'author': 'Álvaro Soto Cunillera',
        'email': 'asotocunillera@gmail.com',
        'year': 2020,
        'version': [1,0,0],
        'license': 'Álvaro Soto Cunillera'
    }
    args = get_args(info)

    main(args)
