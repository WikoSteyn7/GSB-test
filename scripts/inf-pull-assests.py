# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import os
from pyfiglet import Figlet
import json
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import subprocess


f = Figlet()

# Clear the screen
os.system('clear')

# Function to change text color to yellow
def set_yellow_text():
    print("\033[93m", end="")

# Function to reset text color
def reset_text_color():
    print("\033[0m", end="")


print(f.renderText('Import Assets'))

# # Set text color to yellow
# set_yellow_text()

# # Display the notice
# print("\nIMPORTANT NOTICE:")
# print("This process will import assets from your version 1.0 deployment of the Information Assistant")
# print("\nThe assets are as follows:")
# print("- Blobs uploaded to the storage account")
# print("- The Cosmos DB status database")
# print("- Chunk blobs that were created and dropped to the content container in the storage account")
# print("\nOnce these assets are imported, the script will then reindex the chunks.")
# print("If you have changed the default names of any of these services, you will need to update the script.")


# print("\nDo you wish to proceed? (yes/no)")

# # Wait for the user's input
# while True:
#     answer = input("Type 'yes' to accept: ").strip().lower()
#     if answer in ['y', 'yes']:
#         break
#     elif answer in ['n', 'no']:
#         print("You indicated you do not wish to proceed. Exiting.")
#         exit(1)
#     else:
#         print("Please answer yes or no.")

# # Continue with the script after acceptance
# print("You have indicated you wish to continue. Proceeding with the script...")


# old_rg = input("\nWhat is the name of the resource group where the version 1.0 is deployed?")
# print(f"you have confirmed your resource group name is {old_rg}!")

# old_suffix = input("\nWhat is the 5 character suffix of servcies in the resource group where the version 1.0 deployment?")
# print(f"you have confirmed your old service suffix is {old_suffix}!")

# # Reset text color for input prompt
# reset_text_color()


credential = DefaultAzureCredential()
old_suffix = "zvmrv"
old_rg = "infoasst-geearl-446"

# *************************************************************************
# Read required values for the old RG
print("Reading the required values from the old resourge group")


# Get cosmosdb url
command = [
    "az", "cosmosdb", "show",
    "--name", "infoasst-cosmos-" + old_suffix,
    "--resource-group", old_rg,
    "--query", "documentEndpoint",
    "--output", "tsv"
]
result = subprocess.run(command, capture_output=True, text=True)
old_cosmosdb_url = result.stdout.strip()

# Get Keyvault url
command = [
    "az", "keyvault", "show",
    "--name", "infoasst-kv-" + old_suffix,  # Update the name to match your Key Vault naming convention
    "--resource-group", old_rg,
    "--query", "properties.vaultUri",  # Query to get the Key Vault URI
    "--output", "tsv"
]

result = subprocess.run(command, capture_output=True, text=True)
old_keyvault_url = result.stdout.strip()

sClient = SecretClient(vault_url=old_keyvault_url, credential=credential) 
cosmosdb_key = sClient.get_secret('COSMOSDB-KEY') 






# *************************************************************************
# Read required values for the new RG
print("Reading the required values from the new resourge group")

credential = DefaultAzureCredential()
print("Reading values from infra_output.json")
with open('inf_output.json', 'r') as file:
    inf_output = json.load(file)
    
cosmosdb_url = inf_output['properties']['outputs']['AZURE_COSMOSDB_URL']['value']
key_vault_name = inf_output['properties']['outputs']['DEPLOYMENT_KEYVAULT_NAME']['value']
key_vault_url = "https://" + key_vault_name + ".vault.azure.net/"

sClient = SecretClient(vault_url=key_vault_url, credential=credential) 
cosmosdb_key = sClient.get_secret('COSMOSDB-KEY') 







# ***********************************************************
# Import the upload container blobs
# ***********************************************************


# *************************************************************************
# Read required values for the new  & key vault


# *************************************************************************



