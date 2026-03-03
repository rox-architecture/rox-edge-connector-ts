from fastapi import FastAPI, File, UploadFile, Form, status
from src.utils import *
from src.schemas import *
import uvicorn
from dotenv import load_dotenv
import os
from pathlib import Path
import zipfile

#####################################################
#                 Global Variables                  #
#####################################################
app = FastAPI(
    title="KIT-GUI",
    version="0.1.0"
)
load_dotenv() # load all .env variables

#####################################################
#                Frontend Connection                #
#####################################################
from fastapi.middleware.cors import CORSMiddleware
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
] # To allow CORS for GUI connection
# origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#####################################################
#                Global Variables                   #
#####################################################
process_list = []

#####################################################
#            Setup API endpoints                    #
#####################################################
@app.get("/")
def root():
    return {"message": "Edge Connector Started"}

@app.post("/register")
# Purpose: To receive certificate files from the user
def _register_certificates(
        conn_name: str = Form(...),
        tls_crt: UploadFile = File(...),
        tls_key: UploadFile = File(...)
    ):
    
    # save the certificate files
    with open("tls.crt", "wb") as buffer:
        buffer.write(tls_crt.file.read())
    with open("tls.key", "wb") as buffer:
        buffer.write(tls_key.file.read())

    # read .env file and update the CONNECTOR_NAME value
    buffered_lines = []
    update = False
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            raw = line
            stripped = raw.lstrip()
            if stripped.startswith("#") or "=" not in raw:
                buffered_lines.append(raw)
                continue

            k,v = raw.split("=", 1)
            if k.strip() == "CONNECTOR_NAME":
                newline = "\n" if raw.endswith("\n") else ""
                buffered_lines.append(f"{k}={conn_name}{newline}")
                update = True
            else:
                buffered_lines.append(raw)

    # if there was no CONNECTOR_NAME, create it
    if not update:
        if buffered_lines and not buffered_lines[-1].endswith("\n"):
            buffered_lines[-1] += "\n"
        buffered_lines.append(f"CONNECTOR_NAME={conn_name}\n")

    # write back all the variables
    with open(".env", "w") as f:
        f.writelines(buffered_lines)

    # update the value
    load_dotenv(override=True)
    os.environ["CONNECTOR_NAME"] = conn_name
    return {"message": "Certificates registered"}


#####################################################
#            API endpoint Definitions               #
#####################################################
@app.get("/livecheck")
# Purpose: check the edge-connector authentication to the dataspace
async def _livecheck():
    # for DLR dataspace, the liveness is checked by retreiving a token from the dlr dataspace
    if os.getenv('DATASPACE').casefold() == 'DLR'.casefold():
        crt_exists = os.path.isfile("tls.crt")
        key_exists = os.path.isfile("tls.key")
        if crt_exists and key_exists:
            data = await get_token_header()
            print(f'data is {data}')
            if len(data["Authorization"]) > 10: # check if there is token received
                return {"online": True}
        return {"online": False}
    # for T-System dataspace, the liveness is checked by reading an asset
    elif os.getenv('DATASPACE').casefold() == 'TSI'.casefold(): 
        try:
            data = await get_objects('asset', 1, 0)
            return {"online": True}
        except (httpx.RequestError, httpx.HTTPStatusError):
            return {"online": False}
    # for unkonwn dataspace, always return failure
    else:
        return {"online": False}

@app.get("/policies")
# Purpose: To return all available policies 
async def _get_policies(page: int=0, limit: int=100):
    return await get_objects('policy', limit, page)

@app.get("/policy/{id}")
# Purpose: To get the policy definition of the given id
async def _get_policy(id: str):
    return await get_policy(id)

@app.get("/assets")
# Purpose: return all the assets the current user created
async def _get_assets(page: int=0, limit: int=100):
    return await get_objects('asset', limit, page)

@app.get("/contracts")
# Purpose: return all the contracts I defined
async def _get_contracts(page: int=0, limit: int=100):
    return await get_objects('contract', limit, page)

@app.get("/assets/{id}")
# Purpose: return the specific asset detail
async def _get_asset(id: str):
    return await get_asset(id)

@app.delete("/assets/{id}")
# Purpose: To delete an asset
async def _delete_asset(id: str):
    return await delete_asset(id)

@app.delete("/contract/{id}")
# Purpose: To delete the contract definition of the given id
async def _delete_contract(id: str):
    return await delete_contract(id)

@app.post("/kit/basic/create/http") # DEPRECATED
@app.post("/create/basickit")
# Purpose: To create a basic KIT as a HTTP type asset
async def _create_basic_kit(input: BasicKitData):
    data = input.model_dump()
    access_info = data["access_info"]

    # create the KIT Metadata 
    kit_metadata = data["general_info"] | data['additional_info'] 
    kit_metadata['semantic_model'] = data["semantic_model"]
    kit_metadata['asset_type'] = access_info['asset_type']

    # overwrite the domain and standard values based on the .env file
    kit_metadata['standardisation'] = os.getenv('STANDARDISATION')
    kit_metadata['DOMAIN'] = os.getenv('DOMAIN')
    
    if access_info['asset_type'].casefold() == "http".casefold():
        return await create_http_asset(kit_metadata, access_info)

    # in case the access_type is not matching to any specified type, return an empty response
    return {}

@app.post("/kit/composite/create/http") # DEPRECATED
@app.post("/create/compositekit")
# Purpose: To create a composite KIT as a HTTP type asset
async def _create_composite_kit(input: CompositeKitData):
    data = input.model_dump()
    access_info = data["access_info"]
    
    # create the KIT Metadata
    if 'components' in data: # Flattening
        kit_metadata = data["general_info"] | data['additional_info'] | {"components": data["components"]}
    else:
        kit_metadata = data["general_info"] | data['additional_info']
    kit_metadata['asset_type'] = access_info['asset_type']
    kit_metadata['semantic_model'] = data["semantic_model"]

    # overwrite the domain and standard values based on the .env file
    kit_metadata['standardisation'] = os.getenv('STANDARDISATION')
    kit_metadata['DOMAIN'] = os.getenv('DOMAIN')
    
    if access_info['asset_type'].casefold() == "http".casefold():
        return await create_http_asset(kit_metadata, access_info)
    return {}

@app.post("/kit/basic/create/aws")
# Purpose: To create a basic KIT as a amazons3 type asset
async def _create_basic_kit_amazon_asset(input: CompositeKitData):
    # data reshaping
    data_dict = input.dict()
    asset_name = data_dict.pop("asset_name")
    username = data_dict.pop("storage_username")
    password = data_dict.pop("storage_password")
    path = data_dict.pop("object_path")
    bucket = data_dict.pop("bucket_name")
    region = data_dict.pop("storage_region")
    url = data_dict.pop("storage_url")
    data_dict["kit_name"] = asset_name
    data_dict["offerType"] = "data"
    data_dict["kit_type"] = "basic"
    return await create_aws_asset(asset_name, url, bucket, region, path, username, password, data_dict)

@app.post("/contract")
# Purpose: To create a contract definition with the target asset id
async def _create_contract(input: createContract):
    return await create_contract(input.contract_id, input.policy_id, input.asset_id)

@app.get("/federatedcatalog")
# Purpose: return federated catalog
async def _forwarding_data():
    return await get_federated_catalog()

@app.get("/federatedcatalog/{query}")
# Purpose: To filter all offered kits based on the query
async def _search_kits(query: str):
    return await search_by_query(query)

@app.put("/asset")
# Purpose: To edit the asset information
async def _edit_asset(input: editAssetData):
    return await edit_asset(input.context, input.asset_id, input.properties, input.dataAddress)

@app.get("/provider/{provider_id}/offers/{asset_id}")
# Purpose: get all offers linked to an asset id 
async def _kit_contracts(provider_id: str, asset_id: str):
    return await get_target_offer_by_id(provider_id, asset_id)

@app.post("/catalog")
async def _kit_catalog(input: CatalogRequestData):
    if input.kit_name is None:
        return await get_catalog(input.provider_id, input.connector_url)
    else:
        return await get_catalog(input.provider_id, input.connector_url, input.kit_name)

@app.post("/download/kit")
# Purpose: any KIT data will be saved as a file in the local memory. 
#          If the KIT is a service endpoint, then the response is saved as a JSON file.
async def _kit_download(input: KitAccessRequest):
    request_data = input.model_dump()
    # retrieve the kit metadata
    metadata = await get_target_offer_by_id(request_data['provider_id'], request_data['kit_name'])
    if not metadata:
        return {"success": False, "message": "KIT cannot be found"}
    metadata.pop("dcat:distribution", None)
    
    # check that required information is provided 
    if 'kit_type' not in metadata:
        return {"success": False, "message": "Invalid KIT format: kit_type information is missing"}
    if 'asset_type' not in metadata:
        return {"success": False, "message": "Invalid KIT format: asset_type information is missing"}
    
    # extract the policy info from the kit metadata
    policy = metadata.pop('odrl:hasPolicy')[0] # TODO: currently we fetch the first policy

    # trigger the downloading process based on the asset type
    if metadata['asset_type'].casefold() == 'http'.casefold(): # http type case
        success, _ = await http_transfer(request_data, policy, metadata, save_to_file=True, prefix='')
        return {"success": success, "message": "Save-to-file execution completed", "metadata": metadata}
    else: # TODO: aws, azure, etc. cases
        return {"success": False, "message": f"Unknown asset type {metadata['asset_type']}"}


@app.post("/read-content/kit")
# Purpose: any KIT data will be returned as the response to the user request
#          This endpoint is essentially identical to save-to-file, but without saving into a file
async def _kit_read(input: KitAccessRequest):
    request_data = input.model_dump()
    # retrieve the kit metadata
    metadata = await get_target_offer_by_id(request_data['provider_id'], request_data['kit_name'])
    if not metadata:
        return {"success": False, "message": "KIT cannot be found"}
    metadata.pop("dcat:distribution", None)
    
    # check that required information is provided 
    if 'kit_type' not in metadata:
        return {"success": False, "message": "Invalid KIT format: kit_type information is missing"}
    if 'asset_type' not in metadata:
        return {"success": False, "message": "Invalid KIT format: asset_type information is missing"}
    
    # extract the policy info from the kit metadata
    policy = metadata.pop('odrl:hasPolicy')[0] # TODO: currently we fetch the first policy

    # trigger the downloading process based on the asset type
    if metadata['asset_type'].casefold() == 'http'.casefold(): # http type case
        success, response = await http_transfer(request_data, policy, metadata, save_to_file=False, prefix = '')
        return {"success": success, "message": "Read-content execution completed", "metadata": metadata, "response": response}
    else: # TODO: aws, azure, etc. cases
        return {"success": False, "message": f"Unknown asset type {metadata['asset_type']}"}

#TODO:
@app.post("/send-to-else/kit")
# Purpose: basic kit transfer
async def _negotiate(input: KitAccessRequest):
    return {"message": "Not yet implemented"}

@app.post("/http/transfer_2url")
async def _transfer(input: httpTransfer2url):
    if input.assert_type == 'http':
        return await http_transfer_2url(input.originator, input.agreement_id, input.endpoint_url)
    else:
        raise HTTPException(
            status_code = 422,
            detail="Asset type other than http is not implemented"
        )

@app.post("/run/compositekit")
async def _compositekit_runner(input: CanvasData):
    canvas = input.model_dump()
    metadata = canvas['metadata']

    if 'kit_name' not in metadata:
        raise HTTPException( 
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="KIT name for representing this canvas must be provided"
        )

    if 'provider_id' not in metadata:
        folder_name = f'{metadata['kit_name']}'
    else:
        folder_name = f'{metadata['provider_id']}-{metadata['kit_name']}'

    metadata['folder_name'] = folder_name

    result = await composite_kit_execution_blocking(canvas, metadata)
    return {"success": result, "message": "The composite KIT is now being processed"}


@app.get("/run/compositekit/{provider_id}/{kit_name}")
# Purpose: Access all KITs inside a composite KIT alrady saved in the local memory
async def _compositekit_handler(provider_id: str, kit_name: str):
    # find the locally saved kit with the matching kit_name
    kit_workspace_path = Path.cwd() / "KIT-Workspace"
    folder_to_find = f'{provider_id}-{kit_name}'
    kit_folder_path = kit_workspace_path / folder_to_find
    canvas_path = kit_folder_path / 'canvas'

    # check if the kit is located in the local memory
    if not kit_folder_path.is_dir():
        raise HTTPException( 
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Specified KIT folder is not found"
        )
    
    # check if metadata is also saved in the folder
    metadata_file = kit_folder_path / "metadata.json"
    if not metadata_file.is_file():
        raise HTTPException( 
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The KIT metadata is not found or in an invalid format"
        )
    
    # retrieve the metadata and check the required information is present
    with metadata_file.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    if 'kit_type' not in metadata or metadata['kit_type'] != 'composite': # check the kit type is 'composite'
        raise HTTPException( 
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The KIT found is not a composite KIT"
        )
    if not canvas_path.is_file(): # check there is a valid canvas file
        raise HTTPException( 
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Canvas file not found or not a file"
        )

    # If the canvas file is a zip file, unzip it
    if zipfile.is_zipfile(canvas_path):
        zip_path = kit_folder_path / 'canvas.zip'
        canvas_path.rename(zip_path) # rename the zip file so that the extracted canvas file do not conflict with the same name
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(kit_folder_path)
    
    # check if the canvas file exists
    if not canvas_path.is_file():
        raise HTTPException( 
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Canvas file not found"
        )

    # Read the canvas file
    with canvas_path.open('r', encoding='utf-8') as f:
        canvas = json.load(f)
    
    # add provider_id information in the metadata for processing
    metadata['provider_id'] = provider_id
    metadata['folder_name'] = folder_to_find

    # TODO: make this part non-blocking by using proper process handling
    # currently, it is a blocking method (simple)
    result = await composite_kit_execution_blocking(canvas, metadata)
    return {"success": result, "message": "The composite KIT is now being processed"}

@app.get("/negotiations")
# Purpose: Return all the negotiations made in the past
async def _get_negotiations(page: int=0, limit: int=100):
    filter = [{
        "operandLeft": "state",
        "operator": "=",
        "operandRight": "FINALIZED"
    }]
    return await get_objects('negotiation', limit, page, filter)

@app.get("/agreements")
# Purpose: To show all the objects ready-for-transfer
async def _get_agreements(page: int=0, limit: int=100):
    return await get_objects('agreement', limit, page)

@app.delete("/negotiation/{neg_id}")
# Purpose: To terminates the contract negotiation
async def _delete_negotiation(neg_id: str):
    return await delete_negotitation(neg_id)

@app.get("/edrs")
# Purpose: To return all edrs
async def _get_edrs(page: int=0, limit: int=100):
    return await get_objects('edrs', limit, page)

#####################################################
#            Plugin Routers                         #
#####################################################


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
