#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from os import getenv
from typing import Union, NoReturn
from gzip import compress

# 3rd party:
from azure.storage.blob import (
    BlobClient, BlobType, ContentSettings,
    StorageStreamDownloader, StandardBlobTier,
    BlobServiceClient, ContainerClient
)

# Internal:

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


__all__ = [
    "StorageClient"
]


STORAGE_CONNECTION_STRING = getenv("StaticFrontendStorage")

DEFAULT_CONTENT_TYPE = "application/json; charset=utf-8"
DEFAULT_CACHE_CONTROL = "no-cache, max-age=0, stale-while-revalidate=300"
CONTENT_LANGUAGE = 'en-GB'


class StorageClient:
    """
    Azure Storage client.

    Parameters
    ----------
    container: str
        Storage container.

    path: str
        Path to the blob (excluding ``container``). For the listing process,
        the argument is the prefix to filter the files.

    connection_string: str
        Connection string (credentials) to access the storage unit. If not supplied,
        will look for ``DeploymentBlobStorage`` in environment variables.

    content_type: str
        Sets the MIME type of the blob via the ``Content-Type`` header - used
        for uploads only.

        Default: ``application/json; charset=utf-8``

    cache_control: str
        Sets caching rules for the blob via the ``Cache-Control`` header - used
        for uploads only.

        Default: ``no-cache, max-age=0, stale-while-revalidate=300``

    compressed: bool
        If ``True``, will compress the data using `GZip` at maximum level and
        sets ``Content-Encoding`` header for the blob to ``gzip``. If ``False``,
        it will upload the data without any compression.

        Default: ``True``

    content_language: str
        Sets the language of the data via the ``Content-Language`` header - used
        for uploads only.

        Default: ``en-GB``

    tier: str
        Blob access tier - must be one of "Hot", "Cool", or "Archive". [Default: 'Hot']
    """

    def __init__(self, container: str, path: str = str(),
                 connection_string: str = STORAGE_CONNECTION_STRING,
                 content_type: Union[str, None] = DEFAULT_CONTENT_TYPE,
                 cache_control: str = DEFAULT_CACHE_CONTROL, compressed: bool = True,
                 content_disposition: Union[str, None] = None,
                 content_language=CONTENT_LANGUAGE, tier: str = 'Hot', **kwargs):
        self.path = path
        self.compressed = compressed
        self._connection_string = connection_string
        self._container_name = container
        self._tier = getattr(StandardBlobTier, tier, None)

        if self._tier is None:
            raise ValueError(
                "Tier must be one of 'Hot', 'Cool' or 'Archive'. "
                "Got <%r> instead." % tier
            )

        self._content_settings: ContentSettings = ContentSettings(
            content_type=content_type,
            cache_control=cache_control,
            content_encoding="gzip" if self.compressed else None,
            content_language=content_language,
            content_disposition=content_disposition,
            **kwargs
        )

        self.client: BlobClient = BlobClient.from_connection_string(
            conn_str=connection_string,
            container_name=container,
            blob_name=path
        )

    def __enter__(self) -> 'StorageClient':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> NoReturn:
        self.client.close()

    def set_tier(self, tier: str):
        self.client.set_standard_blob_tier(tier)

    def upload(self, data: Union[str, bytes], overwrite: bool = True) -> NoReturn:
        """
        Uploads blob data to the storage.

        Parameters
        ----------
        data: Union[str, bytes]
            Data to be uploaded to the storage.

        overwrite: bool
            Whether to overwrite the file if it already exists. [Default: ``True``]

        Returns
        -------
        NoReturn
        """
        if self.compressed:
            prepped_data = compress(data.encode() if isinstance(data, str) else data)
        else:
            prepped_data = data

        self.client.upload_blob(
            data=prepped_data,
            blob_type=BlobType.BlockBlob,
            content_settings=self._content_settings,
            overwrite=overwrite,
            standard_blob_tier=self._tier
        )
        logging.info(f"Uploaded blob '{self._container_name}/{self.path}'")

    def download(self) -> StorageStreamDownloader:
        data = self.client.download_blob()
        logging.info(f"Downloaded blob '{self._container_name}/{self.path}'")
        return data

    def delete(self):
        self.client.delete_blob()
        logging.info(f"Deleted blob '{self._container_name}/{self.path}'")

    def list_blobs(self):
        with BlobServiceClient.from_connection_string(self._connection_string) as client:
            container: ContainerClient = client.get_container_client(self._container_name)
            for blob in container.list_blobs(name_starts_with=self.path):
                yield blob

    def move_blob(self, target_container: str, target_path: str):
        self.copy_blob(target_container, target_path)
        self.delete()

    def copy_blob(self, target_container: str, target_path: str):
        with BlobServiceClient.from_connection_string(self._connection_string) as client:
            target_blob = client.get_blob_client(target_container, target_path)
            target_blob.start_copy_from_url(self.client.url)
            logging.info(
                f"Copied blob from '{self._container_name}/{self.path}' to "
                f"'{target_container}/{target_path}'"
            )

    def __str__(self):
        return f"Storage object for '{self._container_name}/{self.path}'"

    __iter__ = list_blobs
    __repr__ = __str__
