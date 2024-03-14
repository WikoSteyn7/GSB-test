# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

# This script manages the migration of your content from version 1.0 to 1.1
from pyfiglet import Figlet
import json
import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient



f = Figlet()
print(f.renderText('Migration from 1.0 to 1.1'))
print("Current Working Directory:", os.getcwd())


# *************************************************************************
# Read required values from in_output.json
print("Reading values from inf_output.json")
with open('inf_output.json', 'r') as file:
    inf_output = json.load(file)
    
cosmosdb_url = inf_output['AZURE_COSMOSDB_URL']['value']
cosmosdb_container = inf_output['AZURE_COSMOSDB_LOG_CONTAINER_NAME']['value']
cosmosdb_database = inf_output['AZURE_COSMOSDB_LOG_DATABASE_NAME']['value']
key_vault_name = inf_output['DEPLOYMENT_KEYVAULT_NAME']['value']
key_vault_url = inf_output['DEPLOYMENT_KEYVAULT_URL']['value']

# Read required secrets from azure keyvault
credential = DefaultAzureCredential()
client = SecretClient(vault_url=key_vault_url, credential=credential) 
cosmosdb_key = client.get_secret('COSMOSDB-KEY') 

# *************************************************************************



# *************************************************************************
# Migrate Cosmos DB tags from the old tags container and database to the
# status container and database as these have now been merged
from azure.cosmos import CosmosClient, PartitionKey, exceptions
client = CosmosClient(cosmosdb_url, credential=cosmosdb_key)

try:
    # Attempt to get the database
    database = client.get_database_client(cosmosdb_database)
    container = database.get_container_client(cosmosdb_container)

    # Query these items using SQL query
    items = list(container.query_items(
        query="SELECT * FROM c",
        enable_cross_partition_query=True
    ))

    # Print the results
    for item in items:
        print(item)

except exceptions.CosmosHttpResponseError as e:
    print(f'An error occurred: {e}')
    
# *************************************************************************