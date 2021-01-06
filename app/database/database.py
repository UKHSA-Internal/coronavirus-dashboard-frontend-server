#!/usr/bin python3

"""
<Description of the programme>

Author:        Pouria Hadjibagheri <pouria.hadjibagheri@phe.gov.uk>
Created:       23 Aug 2020
License:       MIT
Contributors:  Pouria Hadjibagheri
"""

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from typing import Union, List, Iterable
from os import getenv
from hashlib import blake2b

# 3rd party:
from azure.cosmos.cosmos_client import CosmosClient
from azure.cosmos import ContainerProxy, DatabaseProxy

# Internal:
from .utils import Credentials, Collection
from .dtypes import ParametersType, ItemType, ResponseType, PaginatedResponse

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


DB_URL = getenv("AzureCosmosHost")
DB_CREDENTIALS = {
    "masterKey": getenv("AzureCosmosKey")
}
DB_NAME = getenv("AzureCosmosDBName")
PREFERRED_LOCATIONS = getenv("AzureCosmosDBLocations", "").split(",")


class CosmosDB:
    def __init__(self, collection: Collection, writer: bool = False):
        credentials = Credentials.READER.value

        if writer:
            credentials = Credentials.WRITER.value

        self.cosmos_client = CosmosClient(
            url=DB_URL,
            credential=credentials,
            preferred_locations=PREFERRED_LOCATIONS
        )
        self.db_client: DatabaseProxy = self.cosmos_client.get_database_client(DB_NAME)
        self.client: ContainerProxy = self.db_client.get_container_client(collection.value)

    def close(self):
        self.cosmos_client.__exit__()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.close()

    def query_iter(self, query: str, params: ParametersType,
                   partition: Union[str, None] = None) -> Iterable[ResponseType]:
        return self.client.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=partition is None or None,
            partition_key=partition
        )

    def query(self, query: str, params: ParametersType,
              partition: Union[str, None] = None) -> List[ResponseType]:
        return list(self.query_iter(query, params, partition))

    def paginated_query(self, query: str, params: ParametersType,
                        partition: Union[str, None] = None, limit: int = 10000,
                        page: Union[int, None] = None) -> PaginatedResponse:
        """

        Parameters
        ----------
        query: str
        params: ParametersType
        partition: Union[str, None]
        limit: int
        page: Union[int, None]
            Page number, starting from zero. [Default: ``None``]
            Where ``None``, returns a lazy iterable of all pages.

        Returns
        -------
        PaginatedResponse

        """
        query_hash = blake2b(query.encode(), digest_size=32).hexdigest()

        response = self.client.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=partition is None or None,
            partition_key=partition,
            max_item_count=limit
        )

        paginated_response = response.by_page(query_hash)

        if page is None:
            return paginated_response

        return list(paginated_response)[page]

    def upsert(self, body: ItemType):
        return self.client.upsert_item(body=body)

    def replace(self, old_item: ItemType, new_item: ItemType):
        return self.client.replace_item(item=old_item, body=new_item)

    def delete(self, item: ItemType):
        return self.client.delete_item(item=item)
