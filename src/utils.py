import httpx
import os
from fastapi import HTTPException
import re
import asyncio
from dotenv import load_dotenv
from pathlib import Path
import json
import shutil
from fastapi.responses import JSONResponse, StreamingResponse


#####################################################
#                 Global Variables                  #
#####################################################
token_url = os.getenv("TOKEN_URL")
base_url = os.getenv("DS_URL")

#####################################################
#                 Utility Functions                 #
#####################################################
# return token value
async def get_token():
    payload = {
        "client_id": "api-client",
        "grant_type": "password",
        "scope": "openid"
    }
    async with httpx.AsyncClient(cert=("tls.crt", "tls.key")) as client:
        response = await client.post(token_url, data=payload)
    try:
        data = response.json()
        get_token.token = data.get("access_token")
    except ValueError:
        get_token.token = None
    return get_token.token

def update_dotenv_vars():
    load_dotenv(override=True) # Reload the .env variables

# TODO
# async def request_sender(url, payload, header, method):
#     async with httpx.AsyncClient() as client:
        

# return header for making http requests
async def get_token_header():
    token = await get_token()
    return {"Authorization": f"Bearer {token}"}

# create a contract definition
async def create_contract(contract_id, policy_id, asset_id):
    token_header = await get_token_header()
    connector_name = os.getenv("CONNECTOR_NAME")
    url = f"{base_url}/connectors/{connector_name}/cp/management/v3/contractdefinitions"
    payload = {
        "@context": {
            "odrl": "http://www.w3.org/ns/odrl/2/"
        },
        "@id": contract_id,
        "accessPolicyId": "all",
        "contractPolicyId": policy_id,
        "assetsSelector": {
            "operandLeft": "https://w3id.org/edc/v0.0.1/ns/id",
            "operator": "=",
            "operandRight": asset_id
        }
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=token_header)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            print(f"HTTP error while creating contract {contract_id}: {exc}")
            raise
        except Exception as exc:
            print(f"Unexpected error while creating contract {contract_id}: {exc}")
            raise
    return response.json()

# retrieve various objects from dataspace
async def get_objects(type, limit=100, page=0, filter=None, connector_name=None): 
    if connector_name is None:
        connector_name = os.getenv("CONNECTOR_NAME")
    if filter is None:
        filter = []
    token_header = await get_token_header()
    if type == 'asset':    
        url = f"{base_url}/connectors/{connector_name}/cp/management/v3/assets/request"
    elif type == 'policy':
        url = f"{base_url}/connectors/{connector_name}/cp/management/v3/policydefinitions/request"
    elif type == 'contract':
        url = f"{base_url}/connectors/{connector_name}/cp/management/v3/contractdefinitions/request"
    elif type == 'negotiation':
        url = f"{base_url}/connectors/{connector_name}/cp/management/v3/contractnegotiations/request"
    elif type == 'agreement':
        url = f"{base_url}/connectors/{connector_name}/cp/management/v3/contractagreements/request"
    elif type == 'edrs':
        url = f"{base_url}/connectors/{connector_name}/cp/management/v3/edrs/request"
    else:
        return None
    
    payload = {
        "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
        "@type": "QuerySpec",
        "offset": page * limit,
        "limit": limit,
        "sortOrder": "DESC",
        "sortField": "id",
        "filterExpression": filter
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=token_header)
        response.raise_for_status()  # optional: raises exception if status >=400
        return response.json()

# create a KIT as an HTTP asset
async def create_http_asset(url, asset_name, method_type, request_type, metadata):
    token_header = await get_token_header()
    connector_name = os.getenv("CONNECTOR_NAME")
    proxyMethod = "false"
    proxyBody = "false"
    if method_type != "GET": 
        proxyMethod = "true"
    if request_type != "none":
        proxyBody = "true"
    print(metadata)
    payload = {
        "@context": {},
        "@id": asset_name,
        "properties": metadata,
        "dataAddress": {
            "@type": "DataAddress",
            "type": "HttpData",
            "baseUrl": url,
            "proxyMethod": proxyMethod,  # allow methods other than GET
            "proxyBody": proxyBody     # allow request bodies
            # "header:authorization": "<some-token>"
        }
    }
    ds_url = f"{base_url}/connectors/{connector_name}/cp/management/v3/assets"
    # create an HTTP asset
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(ds_url, json=payload, headers=token_header)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            # Server returned 4xx/5xx
            raise HTTPException(status_code=exc.response.status_code)

async def create_aws_asset(asset_name, url, bucket, region, path, username, password, metadata):
    token_header = await get_token_header()
    connector_name = os.getenv("CONNECTOR_NAME")
    
    payload = {
        "@context": {},
        "@id": asset_name,
        "properties": metadata,
        "dataAddress": {
            "@type": "DataAddress",
            "type": "AmazonS3",
            "objectName": path,
            "region": region,
            "bucketName": bucket,
            "endpointOverride": url,
            "accessKeyId": username,
            "secretAccessKey": password
        }
    }
    ds_url = f"{base_url}/connectors/{connector_name}/cp/management/v3/assets"
    # create an aws asset
    async with httpx.AsyncClient() as client:
        response = await client.post(ds_url, json=payload, headers=token_header)
    return response.json()

# delete an asset
async def delete_asset(id):
    token_header = await get_token_header()
    connector_name = os.getenv("CONNECTOR_NAME")
    url = f"{base_url}/connectors/{connector_name}/cp/management/v3/assets/{id}"
    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=token_header)
    if response.status_code == 204 or not response.content.strip():
        return True
    return False

# get an asset by ID
async def get_asset(id):
    token_header = await get_token_header()
    connector_name = os.getenv("CONNECTOR_NAME")
    url = f"{base_url}/connectors/{connector_name}/cp/management/v3/assets/{id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=token_header)
    return response.json()

# get a policy definition by ID
async def get_policy(id):
    token_header = await get_token_header()
    connector_name = os.getenv("CONNECTOR_NAME")
    url = f"{base_url}/connectors/{connector_name}/cp/management/v3/policydefinitions/{id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=token_header)
    return response.json()

# delete a contract by ID
async def delete_contract(id):
    token_header = await get_token_header()
    connector_name = os.getenv("CONNECTOR_NAME")
    url = f"{base_url}/connectors/{connector_name}/cp/management/v3/contractdefinitions/{id}"
    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=token_header)
    if response.status_code == 204 or not response.content.strip():
        return True
    return False

# return the federated catalog
async def get_federated_catalog():
    url = f"{base_url}/federated/catalog"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    response.raise_for_status()
    return response.json()

# return the asset metadata provided by the target provider
# TODO: re-implement this without using the federated catalogue
async def get_target_offer_by_id(provider_id, asset_id):
    fed_catalog = await get_federated_catalog()

    for cat in fed_catalog:
        if cat["dspace:participantId"] != provider_id:
            continue

        datasets = cat["dcat:dataset"]
        if not isinstance(datasets, list): # caset datasets to an array
            datasets = [datasets]
        if not datasets: # skip if datasets is empty
            continue

        for asset in datasets:
            if asset["kit_name"] != asset_id:
                continue
            return asset
    return {}


# return a negotiation id
# TODO: currently we always create a new one without checking existing valid one
async def create_http_negotiation(connector_name, connector_url, policy, bpn, asset_id, token_header):
    url = f"{base_url}/connectors/{connector_name}/cp/management/v3/edrs"
    payload = {
        "@context": {
            "odrl": "http://www.w3.org/ns/odrl/2/"
        },
        "counterPartyAddress": connector_url,
        "protocol": "dataspace-protocol-http",
        "policy": policy | {"odrl:assigner": {"@id": bpn}, "odrl:target": {"@id": asset_id}}
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=token_header)
        response.raise_for_status()
        print(f'Negotiation id: {response.json()["@id"]}')
        return response.json()["@id"]

# return the HTTP asset access_token and endpoint
async def get_transfer_credentials(connector_name, asset_id, token_header):
    url = f"{base_url}/connectors/{connector_name}/cp/management/v3/edrs/request"
    payload = {
    "@context": {},
    "@type": "QuerySpec",
    "filterExpression": [
            {
                "operandLeft": "assetId",
                "operator": "=",
                "operandRight": asset_id
            }
        ]
    }
    # obtain the transfer id
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=token_header)
        response.raise_for_status()
        if response.json() == []: return None, None
        transfer_id = response.json()[0]["transferProcessId"]
        print(f'Transfer id: {transfer_id}')

    # use the transfer id to get the access url and token
    url = f"{base_url}/connectors/{connector_name}/cp/management/v3/edrs/{transfer_id}/dataaddress"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=token_header)
        response.raise_for_status()
    access_token = response.json()["authorization"]
    endpoint = response.json()["endpoint"]
    return endpoint, access_token


# TODO: currently, we create negotiation id every single time
async def http_transfer(connector_url, bpn, policy, asset_id, payload=None, post_action=False):
    token_header = await get_token_header()
    connector_name = os.getenv("CONNECTOR_NAME")

    # Search for an existing EDR negotiation id
    endpoint, token = await get_transfer_credentials(connector_name, asset_id, token_header)
    print(endpoint)

    # If we need to create a new negotiation id
    if endpoint == None:
        negotiation_id = await create_http_negotiation(connector_name, connector_url, policy, bpn, asset_id, token_header)
        await asyncio.sleep(5) # we need around 10 seconds to wait before the agreement id is generated
        endpoint, token = await get_transfer_credentials(connector_name, asset_id, token_header)

    # Activate transfer
    print("Data transfer started")
    headers = {"Authorization": token}
    async with httpx.AsyncClient() as client:
        
        if payload == None:
            response = await client.get(endpoint, headers=headers)
        else:
            response = await client.post(endpoint, headers=headers, json=payload)

    # Handle file correctly based on the content-type
    print("Starting the data transfer")

    # create the workspace folder if not exist
    workspace = Path("KIT-Workspace")
    workspace.mkdir(parents=True, exist_ok=True)

    # get the target asset's metadata to get information on how to handle data
    asset_metadata = await get_target_offer_by_id(bpn, asset_id)
    asset_metadata.pop("dcat:distribution", None)
    print(asset_metadata)
    kit_name = asset_metadata["kit_name"]
    if "default_file_name" in asset_metadata:
        filename = asset_metadata["default_file_name"]
    else:
        filename = kit_name
    
    kit_folder = workspace / kit_name
    file_path = kit_folder / filename

    # delete the kit folder, if exists, for overwritting
    if kit_folder.exists():
        shutil.rmtree(kit_folder)
    kit_folder.mkdir(parents=True, exist_ok=True)

    # TODO: live data stream must be handled here
    livedata = False
    
    # write the metadata in the folder
    metadata_path = workspace / kit_name / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(asset_metadata, f, indent=4, ensure_ascii=False)

    if not livedata: # save into a file
        with open(file_path, "wb") as f:
            async for chunk in response.aiter_bytes():
                f.write(chunk)
    
        return {"message": "Data saved into a file"}
    else:
        return {"message": "Live data streaming successful"}


# Convert the search query into tokens, otherwise, return None
def parse_query(query):
    operators = r"(==|!=|<=|<|>=|>|contains|startswith|endswith)"
    identifier = r"[A-Za-z_]\w*"
    quoted = r"'[^']*'|\"[^\"]*\""
    string_pattern = rf"({identifier}|{quoted}|\d+(?:\.\d+)?)"
    clause_pattern = rf"{string_pattern}\s*{operators}\s*{string_pattern}"
    separator_pattern = r"\s*(?:and|&)\s*"
    full_pattern = rf"^{clause_pattern}({separator_pattern}{clause_pattern})*$"

    if not re.fullmatch(full_pattern, query.strip()):
        return None # ill format query
    
    clauses = re.split(separator_pattern, query.strip())
    tokenized = []
    clause_regex = re.compile(rf"{string_pattern}\s*{operators}\s*{string_pattern}")

    for clause in clauses:
        match = clause_regex.fullmatch(clause)
        if not match:
            return None  # safety check
        left, op, right = match.group(1), match.group(2), match.group(3)

        # Strip quotation marks
        left = left.strip("'\"")
        right = right.strip("'\"")
        tokenized.append((left, op, right))

    return tokenized


# given dcat:dataset, it checks whether the search query is satisfied
def check_match(data, tokens):
    for lhs, op, rhs in tokens:
        lhs = lhs.casefold()
        if lhs not in data: # if there is no key found
            return False
        
        value = data[lhs]
        try:
            if isinstance(value, (int, float)):
                rhs = type(value)(rhs) # match the value type
        except Exception:
            return False

        if isinstance(value, str) and isinstance(rhs, str):
            value = value.casefold()
            rhs = rhs.casefold()

        # Comparison
        if op == "==":
            ok = value == rhs
        elif op == "!=":
            ok = value != rhs
        elif op in ("<", "<=", ">", ">="):
            if not isinstance(value, (int, float)):
                return False
            if op == "<":
                ok = value < rhs
            elif op == "<=":
                ok = value <= rhs
            elif op == ">":
                ok = value > rhs
            else:
                ok = value >= rhs
        elif op == "contains":
            ok = isinstance(value, str) and rhs in value
        elif op == "startswith":
            ok = isinstance(value, str) and value.startswith(rhs)
        elif op == "endswith":
            ok = isinstance(value, str) and value.endswith(rhs)
        else:
            return False  # unknown operator
        
        if not ok:
            return False
    return True

# Return the kits that match to the search query
async def search_by_query(query):
    # tokenize the search query
    tokens  = parse_query(query)
    if tokens is None:
        return {}

    fed_catalog = await get_federated_catalog()
    if tokens is None:
        return fed_catalog

    for catalog in fed_catalog:
        datasets = catalog["dcat:dataset"]
        bpn = catalog["dspace:participantId"]
        if not isinstance(datasets, list): # caset datasets to an array
            datasets = [datasets]
        if not datasets: # skip if datasets is empty
            continue

        filtered_datasets = []
        for dataset in datasets:
            preprocessed = {**{key : value for key, value in dataset.items() 
                                if key not in {"@id","@type","odrl:hasPolicy","dcat:distribution","semantic_model",}},
                            **dataset.get("semantic_model", {})}
            preprocessed = {k.casefold(): v for k, v in preprocessed.items()} # make key all casefold()
            preprocessed["bpn"] = bpn
            if check_match(preprocessed, tokens):
                filtered_datasets.append(dataset)
        catalog["dcat:dataset"] = filtered_datasets
    return fed_catalog

# To edit an asset details with new data
async def edit_asset(context, asset_id, properties, dataAddress):
    token_header = await get_token_header()
    connector_name = os.getenv("CONNECTOR_NAME")
    payload = {
        "@context": context,
        "@id": asset_id,
        "properties": properties,
        "dataAddress": dataAddress
    }
    ds_url = f"{base_url}/connectors/{connector_name}/cp/management/v3/assets"
    # create an aws asset
    async with httpx.AsyncClient() as client:
        response = await client.put(ds_url, json=payload, headers=token_header)
    try:
        return response.json()
    except:
        return {"status_code": response.status_code, "body": response.text or "No content"}

# delete negotiation
async def delete_negotitation(id):
    token_header = await get_token_header()
    connector_name = os.getenv("CONNECTOR_NAME")

    ds_url = f"{base_url}/connectors/{connector_name}/cp/management/v3/contractnegotiations/{id}/terminate"
    payload = {
        "@context": {
            "@vocab": "https://w3id.org/edc/v0.0.1/ns/"
        },
        "@type": "https://w3id.org/edc/v0.0.1/ns/TerminateNegotiation",
        "@id": id,
        "reason": "User's request to terminate"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(ds_url, json=payload, headers=token_header)
        print(response.status_code)
    try:
        print (response.json())
        return response.json()
    except:
        return {"status_code": response.status_code, "body": response.text or "No content"}
    