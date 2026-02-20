import httpx
import os
from fastapi import HTTPException
import re
import asyncio
from dotenv import load_dotenv
from pathlib import Path
import json
from urllib.parse import unquote
import shutil
from fastapi.responses import JSONResponse, StreamingResponse


#####################################################
#                 Global Variables                  #
#####################################################
token_url = os.getenv("TOKEN_URL")
base_url = os.getenv("BASE_URL")
connector = os.getenv("CONNECTOR_NAME")

#####################################################
#                 Utility Functions                 #
#####################################################

# return header for making http requests
async def get_token_header():
    # If the edge-connector is interacting with the DLR dataspace
    if os.getenv('DATASPACE').casefold() == 'DLR'.casefold():
        token_url = os.getenv("TOKEN_URL")
        payload = {
            "client_id": "api-client",
            "grant_type": "password",
            "scope": "openid"
        }
        async with httpx.AsyncClient(cert=("tls.crt", "tls.key")) as client:
            print(f"Dataspace API triggered: {token_url}")
            response = await client.post(token_url, data=payload)
        try:
            data = response.json()
            get_token_header.token = data.get("access_token")
        except ValueError:
            get_token_header.token = None
        return {"Authorization": f"Bearer {get_token_header.token}"}
    # If the edge-connector is interating with the T-System dataspace
    elif os.getenv('DATASPACE').casefold() == 'TSI'.casefold():
        api_key = os.getenv('API-KEY')
        return {"X-Api-Key": f"{api_key}", 
                "content-type": "application/json"}

# retrieve various objects from dataspace
async def get_objects(type, limit=100, page=0): 
    address_book = { # maps the user request to the correct URL in the .env file
        'asset' : 'ASSET_READ_URL',
        'policy' : 'POLICY_READ_URL',
        'contract' : 'CONTRACT_READ_URL',
        'negotiation' : 'NEGOTIATION_READ_URL',
        'agreement' : 'AGREEMENT_READ_URL',
        'edr' : 'EDR_READ_URL'
    }

    url = os.getenv( address_book[type] ) # fetch the correct endpoint URL
    token_header = await get_token_header()

    filter = [] 
    if type == "asset": # filter out non-kit assets
        filter = [
            # {
            #     "operandLeft": "https://w3id.org/edc/v0.0.1/ns/standardisation",
            #     "operator": "=",
            #     "operandRight": "kit" 
            # }
        ]

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
        print(f"Dataspace API triggered: {url}")
        response = await client.post(url, json=payload, headers=token_header)
        response.raise_for_status()  # optional: raises exception if status >=400
        print(response.json())
        return response.json()
    

# create a contract definition
async def create_contract(contract_id, policy_id, asset_id):
    token_header = await get_token_header()
    url = os.getenv("CONTRACT_CREATE_URL")
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
            print(f"Dataspace API triggered: {url}")
            response = await client.post(url, json=payload, headers=token_header)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            print(f"HTTP error while creating contract {contract_id}: {exc}")
            raise
        except Exception as exc:
            print(f"Unexpected error while creating contract {contract_id}: {exc}")
            raise
    return response.json()


# create a KIT as an HTTP asset 
async def create_http_asset(kit_metadata, access_info):
    # dataspace url and header string
    url = os.getenv("ASSET_CREATE_URL")
    token_header = await get_token_header() 

    # mapping
    asset_name = kit_metadata['kit_name']
    asset_metadata = kit_metadata

    proxy_method = 'true' if access_info['method'].casefold() != 'GET'.casefold() else 'false'
    proxy_body = 'true' if access_info['need_req_body'] else 'false'

    # build the header (not the header to datasapce)
    proxy_header = {}
    if 'header' in access_info:
        proxy_header = {f'header:{k}': v for k,v in access_info['header']}

    payload = {
        "@context": {},
        "@id": asset_name,
        "properties": asset_metadata,
        "dataAddress": {
            "@type": "DataAddress",
            "type": "HttpData",
            "baseUrl": url,
            "proxyMethod": proxy_method,  # allow methods other than GET
            "proxyBody": proxy_body     # allow request bodies
            # "header:authorization": "<some-token>"
        }
    }
    # add the header to the payload
    payload['dataAddress'].update(proxy_header)
    
    # create an HTTP asset
    async with httpx.AsyncClient() as client:
        try:
            print(f"Dataspace API triggered: {url}")
            response = await client.post(url, json=payload, headers=token_header)
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
    template = os.getenv("ASSET_DELETE_BY_ID_URL")
    url = template.replace("{id}", id)
    async with httpx.AsyncClient() as client:
        print(f"Dataspace API triggered: {url}")
        response = await client.delete(url, headers=token_header)
    if response.status_code == 204 or not response.content.strip():
        return True
    return False

# get an asset by ID
async def get_asset(id):
    token_header = await get_token_header()
    template = os.getenv("ASSET_READ_BY_ID_URL")
    url = template.replace("{id}", id)
    async with httpx.AsyncClient() as client:
        print(f"Dataspace API triggered: {url}")
        response = await client.get(url, headers=token_header)
    return response.json()

# get a policy definition by ID
async def get_policy(id):
    token_header = await get_token_header()
    template = os.getenv("POLICY_READ_BY_ID_URL")
    url = template.replace("{id}", id)
    async with httpx.AsyncClient() as client:
        print(f"Dataspace API triggered: {url}")
        response = await client.get(url, headers=token_header)
    return response.json()

# delete a contract by ID
async def delete_contract(id):
    token_header = await get_token_header()
    template = os.getenv("CONTRACT_DELETE_BY_ID_URL")
    url = template.replace("{id}", id)
    async with httpx.AsyncClient() as client:
        print(f"Dataspace API triggered: {url}")
        response = await client.delete(url, headers=token_header)
    if response.status_code == 204 or not response.content.strip():
        return True
    return False

# return the federated catalog
async def get_federated_catalog():
    url = os.getenv("FEDERATED_CAT_URL") 
    async with httpx.AsyncClient() as client:
        print(f"Dataspace API triggered: {url}")
        response = await client.get(url)
    response.raise_for_status()
    return response.json()

# return the asset metadata provided by the target provider
# TODO: re-implement this without using the federated catalogue
async def get_target_offer_by_id(provider_id, asset_id):
    fed_catalog = await get_federated_catalog()
    for cat in fed_catalog:
        participantId = cat["dspace:participantId"]
        originator = cat['originator']
        if participantId != provider_id:
            continue
        datasets = cat["dcat:dataset"]
        if not isinstance(datasets, list): # cast datasets into an array
            datasets = [datasets]
        if not datasets: # skip if datasets is empty
            continue
        for asset in datasets:
            # TODO: have better filtering out of the assets not meeting the KIT format
            if 'kit_name' not in asset: 
                continue # if no kit_name found, skip
            if asset["kit_name"] != asset_id:
                continue # if kit_name not match with the requested string, skip

            # add additional useful information
            asset['participantId'] = participantId
            asset['originator'] = originator
            asset['policy'] = asset['odrl:hasPolicy']
            return asset
    return {}


# return a negotiation id
# TODO: currently we always create a new one without checking existing valid one
async def create_http_negotiation(connector_url, policy, bpn, asset_id, token_header):
    url = os.getenv("EDR_NEGOTIATION_URL")
    payload = {
        "@context": {
            "odrl": "http://www.w3.org/ns/odrl/2/"
        },
        "counterPartyAddress": connector_url,
        "protocol": "dataspace-protocol-http",
        "policy": policy | {"odrl:assigner": {"@id": bpn}, "odrl:target": {"@id": asset_id}}
    }
    async with httpx.AsyncClient() as client:
        print(f"Dataspace API triggered: {url}")
        response = await client.post(url, json=payload, headers=token_header)
        response.raise_for_status()
        print(f'Negotiation id: {response.json()["@id"]}')
        return response.json()["@id"]

# return the HTTP asset access_token and endpoint
async def get_transfer_credentials(asset_id, token_header):
    url = os.getenv("EDR_READ_URL")
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
        print(f"Dataspace API triggered: {url}")
        response = await client.post(url, json=payload, headers=token_header)
        response.raise_for_status()
        if response.json() == []: return None, None
        transfer_id = response.json()[0]["transferProcessId"]
        print(f'Transfer id: {transfer_id}')

    # use the transfer id to get the access url and token
    template = os.getenv("EDR_DATA_ADDRESS_URL")
    url = template.replace("{transfer_id}", transfer_id)
    async with httpx.AsyncClient() as client:
        print(f"Dataspace API triggered: {url}")
        response = await client.get(url, headers=token_header)
        response.raise_for_status()
    access_token = response.json()["authorization"]
    endpoint = response.json()["endpoint"]
    return endpoint, access_token


# TODO: currently, we create negotiation id every single time
async def http_transfer(request_data, policy, metadata):
    token_header = await get_token_header()
    asset_id = request_data['kit_name']
    connector_url = request_data['connector_url']
    bpn = request_data['provider_id']
    payload = request_data['request_body'] if 'request_body' in request_data else None

    # Search for an existing EDR negotiation id
    print(f"Target asset to download: {asset_id}")
    endpoint, token = await get_transfer_credentials(asset_id, token_header)
    print(f'endpoint: {endpoint}')

    if endpoint == None:  # In case, we need to create a new negotiation id
        print('Creating a negotiation')
        negotiation_id = await create_http_negotiation(connector_url, policy, bpn, asset_id, token_header)
        await asyncio.sleep(5) # we need around 10 seconds to wait before the agreement id is generated
        endpoint, token = await get_transfer_credentials(asset_id, token_header)
    print(endpoint)
    
    # Activate transfer
    print("Data transfer started")
    headers = {"Authorization": token}
    async with httpx.AsyncClient() as client:
        print(f"Dataspace API triggered: {endpoint}")
        if payload == None:
            response = await client.get(endpoint, headers=headers)
        else:
            response = await client.post(endpoint, headers=headers, json=payload)

    # Now, we need to save KIT into the local drive
    print("KIT is being saved to the local drive")
    # create the workspace folder if not exist
    workspace = Path("KIT-Workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    print(metadata)

    # to save into a file, we need to know the file name
    filename = None
    
    # if the provider specified the file name, then we use it
    if 'default_file_name' in metadata:
        filename = metadata['default_file_name']
    else: # if not, then check if the provider provide content-disposition header
        name_string = response.headers.get('Content-Disposition')
        if name_string:
            # handle the case of "filename*=" using regex
            m = re.search(r"filename\*\s*=\s*([^;]+)", name_string, flags=re.IGNORECASE)
            if m:
                value = m.group(1).strip().strip('"')
                if "''" in value:
                    _, encoded = value.split("''", 1)
                    filename = unquote(encoded)
                else:
                    filename = value
            else:
                m = re.search(r"filename\s*=\s*([^;]+)", name_string, flags=re.IGNORECASE)
                if m:
                    filename = m.group(1).strip().strip('"')
        # TODO: we can also generate file name based on the content-type
    
    # if file name is NOT given, we use the asset id as the file name
    filename = asset_id    
    kit_folder = workspace / f'{bpn}-{asset_id}'
    file_path = kit_folder / filename

    # check if overwriting is enabled
    overwrite = False if 'overwrite' not in request_data else request_data['overwrite']
    if kit_folder.exists() and overwrite:
        shutil.rmtree(kit_folder) # delete the already downloaded KIT
    kit_folder.mkdir(parents=True, exist_ok=True) # recreate the folder
    
    # write the metadata in the folder
    metadata_path = kit_folder / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    # save KIT into a file
    with open(file_path, "wb") as f:
        async for chunk in response.aiter_bytes():
            f.write(chunk)

    return True


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
    url = os.getenv("ASSET_EDIT_URL")
    payload = {
        "@context": context,
        "@id": asset_id,
        "properties": properties,
        "dataAddress": dataAddress
    }
    async with httpx.AsyncClient() as client:
        print(f"Dataspace API triggered: {url}")
        response = await client.put(url, json=payload, headers=token_header)
    try:
        return response.json()
    except:
        return {"status_code": response.status_code, "body": response.text or "No content"}

# delete negotiation
async def delete_negotitation(id):
    token_header = await get_token_header()
    template = os.getenv("NEGOTIATION_DELETE_BY_ID_URL")
    url = template.replace("{id}", id)

    payload = {
        "@context": {
            "@vocab": "https://w3id.org/edc/v0.0.1/ns/"
        },
        "@type": "https://w3id.org/edc/v0.0.1/ns/TerminateNegotiation",
        "@id": id,
        "reason": "User's request to terminate"
    }
    async with httpx.AsyncClient() as client:
        print(f"Dataspace API triggered: {url}")
        response = await client.post(url, json=payload, headers=token_header)
        print(response.status_code)
    try:
        print (response.json())
        return response.json()
    except:
        return {"status_code": response.status_code, "body": response.text or "No content"}
    
    
async def http_transfer_2url(originator, agreement_id, endpoint_url):
    
    """
    Transfer data from an offer with an Agreement to an HTTP endpoint.
    
    originator: The DSP address of the Connector providing the offer.
    agreement_id: The ID of the Agreement for the offer.
    endpoint_url:  The URL of your endpoint where the data should be sent to.
    """
    
    token_header = await get_token_header()
    
    url = f"{base_url}/connectors/{connector}/cp/management/v3/transferprocesses"
    payload = {
    "@context": {
        "odrl": "http://www.w3.org/ns/odrl/2/"
    },
    "counterPartyAddress": originator,
    "contractId": agreement_id,
    "transferType": "HttpData-PUSH",
    "dataDestination": {
        "type": "HttpData",
        "baseUrl": endpoint_url,
    },
    "protocol": "dataspace-protocol-http"
    }
    
    async with httpx.AsyncClient() as client:
        response = client.post(url, json=payload, headers=token_header)

        response.raise_for_status()
        
        print(response.content)
        response.raise_for_status()
        
        transfer_id = response.json()["@id"]
        print(f"Started Transfer with ID: {transfer_id}")

        # confirm it worked
        url = f"{base_url}/connectors/{connector}/cp/management/v3/transferprocesses/{transfer_id}"

        response = client.get(url, headers=token_header)
        response.raise_for_status()
        print(f"Transfer data:\n")
        return response.json()