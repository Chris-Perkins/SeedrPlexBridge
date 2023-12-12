import os
from seedr_client import SeedrClient
from processed_file_registry import ProcessedFileRegistry

'''
The bridge between Seedr and the local system.

Scans seedr for new files.
New files are then downloaded to a file path used by a media server.

What could be cool: Hook this back up to Discord; post a message in a channel
after the movie is done downloading
'''
class MediaBridgeManager():

    def __init__(self, 
                 seedr_client: SeedrClient, 
                 processed_file_registry: ProcessedFileRegistry,
    ) -> None:
        self.seedr_client = seedr_client
        self.processed_file_registry = processed_file_registry
    
    '''
    Scans the input folder_id for any new files. New files are uploaded to
    the specified base download path, postfixed by their location in seedr.

    After scanning, the catalog is refreshed.
    That's a little wasteful, but whatever.
    '''
    async def scan(self, folder_id: int, folder_name: str, base_download_path: str):
        folder_contents = self.seedr_client.list_folder_contents(folder_id=folder_id)
        self.__recursively_process_seedr_folder(
            folder_contents=folder_contents, 
            base_download_path=base_download_path,
            base_folder_name=folder_name,
        )
    
    '''
    Recursively processes the input folder contents, including all children
    folders.

    A file is processed once the contents of the folder have been downloaded,
    and marked in the registry as processed.

    If a folder or file is already present in the registry and has not been
    updated since it was added to the registry, it is skipped
    such that an object will only ever be processed once.

    After a folder has been processed, it is deleted to save storage.
    '''
    def __recursively_process_seedr_folder(
            self, 
            folder_contents: any,
            base_folder_name: str, 
            base_download_path: str, 
            cur_path: str = "",
    ):
        for folder in folder_contents['folders']:
            folder_id = folder['id']
            folder_name = folder['name']
            timestamp = folder['last_update']
            
            if self.processed_file_registry.is_processed(folder_id, timestamp):
                continue

            print(f"Scanning {folder}")
            child_folder_contents = self.seedr_client.list_folder_contents(folder_id)
            # for some reason, a folder name includes the name of parent folders
            # so we don't need to keep a track of the path manually
            self.__recursively_process_seedr_folder(
                folder_contents=child_folder_contents, 
                base_download_path=base_download_path, 
                base_folder_name=base_folder_name,
                cur_path=folder_name,
            )
            self.processed_file_registry.mark_processed(item_id=folder_id, timestamp=timestamp)
            self.seedr_client.delete_folder(folder_id=folder_id)
            print(f"Finished scanning and deleted {folder}")

        for file in folder_contents['files']:
            file_name = file['name']
            valid_cur_path = cur_path.replace(base_folder_name, "").replace("\"", "").split("/")
            output_path = os.path.join(base_download_path, *valid_cur_path, file_name)
            print(output_path)
            self.seedr_client.download_file(
                file_id=file['id'], 
                destination_path=output_path,
            )