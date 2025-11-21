#!python3
import sys
import argparse
import requests
import urllib3
import pandas as pd
# get python environment variables
from dotenv import load_dotenv

from panopto_folders import PanoptoFolders
from pathlib import Path
from os.path import dirname, join, abspath
import os
from pathlib import Path
from dotenv import load_dotenv
import argparse

# Load .env from project root (parent of this file's directory)
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")

sys.path.insert(0, abspath(join(dirname(__file__), '..', 'common')))
from panopto_oauth2 import PanoptoOAuth2


# Top level folder is represented by zero GUID.
# However, it is not the real folder and some API beahves differently than actual folder.
GUID_TOPLEVEL = '00000000-0000-0000-0000-000000000000'

def parse_argument():
    parser = argparse.ArgumentParser(description='Sample of Folders API')

    parser.add_argument(
        '--server',
        dest='server',
        required=False,
        default=os.getenv("SERVER"),
        help='Server name as FQDN (or set SERVER in .env)'
    )

    parser.add_argument(
        '--client-id',
        dest='client_id',
        required=False,
        default=os.getenv("CLIENT_ID"),
        help='Client ID of OAuth2 client (or set CLIENT_ID in .env)'
    )

    parser.add_argument(
        '--client-secret',
        dest='client_secret',
        required=False,
        default=os.getenv("CLIENT_SECRET"),
        help='Client Secret of OAuth2 client (or set CLIENT_SECRET in .env)'
    )

    parser.add_argument(
        '--skip-verify',
        dest='skip_verify',
        action='store_true',
        required=False,
        help='Skip SSL certificate verification. (Never apply to the production code)'
    )

    args = parser.parse_args()

    # Optional: enforce that they are set either via CLI or .env
    missing = [name for name in ("server", "client_id", "client_secret")
               if getattr(args, name) is None]

    if missing:
        parser.error(
            "Missing required values: {}. Provide via CLI or .env".format(
                ", ".join(missing)
            )
        )

    return args


def main():
    load_dotenv()  # take environment variables from .env file
    print()
    args = parse_argument()

    # all_folders = [] # Let's start off with an empty array for our folders

    if args.skip_verify:
        # This line is needed to suppress annoying warning message.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Use requests module's Session object in this example.
    # ref. https://2.python-requests.org/en/master/user/advanced/#session-objects
    requests_session = requests.Session()
    requests_session.verify = not args.skip_verify
    
    # Load OAuth2 logic
    oauth2 = PanoptoOAuth2(args.server, args.client_id, args.client_secret, not args.skip_verify)

    # Load Folders API logic
    panopto_folders_api = PanoptoFolders(args.server, not args.skip_verify, oauth2)
    
    print("\nGetting Panopto Folders First\n")
    all_folders = pd.DataFrame(get_sub_folders(panopto_folders_api, GUID_TOPLEVEL))
    print("A total of {} folders were received.".format(len(all_folders)))
    all_folders.info()
    all_folders.to_csv('all_panopto_folders.csv', index=False)

    print ("\nGetting Panopto Video Sessions for each folder\n")
    all_folders.reset_index() # Make sure we start at the beginning
    #row_count = 5
    all_sessions = [] # Let's store the sessions here
    for index, folder in all_folders.iterrows():
        new_sessions = get_sessions(panopto_folders_api, folder)
        #print(new_sessions)
        #print("From this folder {} sessions were received.".format(len(new_sessions)))
        for session in new_sessions:
            all_sessions.append(session)
        #row_count -= 1
        #if row_count <= 0:
        #    break
    
    print("A total of {} sessions were received.".format(len(all_sessions)))
    all_session_df = pd.DataFrame(all_sessions)
    #print("The dataframe has {} sessions.".format(len(all_session_df)))
    all_session_df.info()
    all_session_df.to_csv('all_panopto_sessions.csv', index=False)
    # all_session_df.to_csv('all_pantopo_session_2.csv', index=True)
    print ("\nDone")
    quit()

def get_folder(panopto_folders_api, folder_id):
    if folder_id == GUID_TOPLEVEL:
        return None
    folder = panopto_folders_api.get_folder(folder_id)

def get_sub_folders(panopto_folders_api, current_folder_id, folders_found_so_far = []):
    children_folders = panopto_folders_api.get_children(current_folder_id)
    if (len(children_folders) > 0):
        for folder in children_folders:
            if folder['Id'] is None:
                folder['Id'] = GUID_TOPLEVEL
            if folder['ParentFolder'] is None:
                folder['ParentFolder'] = {'Id' : GUID_TOPLEVEL}
            folder_details = {
                'folder_id' : folder['Id'],
                'folder_name' : folder['Name'],
                'parent_folder': folder['ParentFolder']['Id']
            }
            folders_found_so_far.append(folder_details)
            get_sub_folders(panopto_folders_api, folder['Id'], folders_found_so_far)
    return folders_found_so_far


def list_sessions(panopto_folders_api, folder):
    print('Sessions in the folder:')
    for entry in panopto_folders_api.get_sessions(folder['folder_id']):
        print('  {0}: {1}'.format(entry['Id'], entry['folder_name']))
    


def get_sessions(panopto_folders_api, folder):
    #print('Sessions in the folder:')
    return_sessions = []
    for entry in panopto_folders_api.get_sessions(folder['folder_id']):
        session_details = flatten_session_details(entry)
        return_sessions.append(session_details)
        #print('  {0}: {1}'.format(entry['Id'], entry['folder_name']))
        #print(entry)
    print("From this folder {} sessions were received.".format(len(return_sessions)))
    return return_sessions

def flatten_session_details(session):
    session_details = {
        'session_name': session['Name'],
        'session_id': session['Id'],
        'percent_completed': session['PercentCompleted'],
        'description': session['Description'],
        'start_time': session['StartTime'],
        'duration': session['Duration'],
        'created_userid': session['CreatedBy']['Id'],
        'created_username': session['CreatedBy']['Username'],
        'folder_id': session['FolderDetails']['Id'],
        'folder_name': session['FolderDetails']['Name'],
        'viewer_url': session['Urls']['ViewerUrl'],
    }
    return session_details

if __name__ == '__main__':
    main()
