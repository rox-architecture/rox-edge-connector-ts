from fastapi import FastAPI, File, UploadFile, Form
from src.utils import *
from src.schemas import *
import uvicorn
import os

#####################################################
#                 Global Variables                  #
#####################################################
app = FastAPI(
    title="KIT-Interface",
    version="0.0.1"
)
load_dotenv() # load all .env variables

#####################################################
#                Frontend Connection                #
#####################################################
from fastapi.middleware.cors import CORSMiddleware
origins = ["*"] # To allow CORS for GUI connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#####################################################
#            API endpoint Definitions               #
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
    with open("tls.crt", "wb") as buffer:
        buffer.write(tls_crt.file.read())
    with open("tls.key", "wb") as buffer:
        buffer.write(tls_key.file.read())

    existing = {}
    with open(".env", "r") as f: # Read existing .env if it exists
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                existing[k] = v
    existing["CONNECTOR_NAME"] = conn_name
    
    with open(".env", "w") as f: # Write back all variables
        for k, v in existing.items():
            f.write(f"{k}={v}\n") 

    update_dotenv_vars()
    return {"message": "Certificates registered"}

@app.get("/livecheck")
# Purpose: To check the Edge Connector status
async def _livecheck():
    crt_exists = os.path.isfile("tls.crt")
    key_exists = os.path.isfile("tls.key")
    if crt_exists and key_exists:
        return {"message": await get_token_header()} 
    else:
        return {"message": {}}

@app.get("/policies")
# Purpose: To return all available policies 
async def _get_policies(page: int=0, limit: int=100):
    return await get_objects('policy', limit, page)

@app.get("/assets")
# Purpose: return all the assets the current user created
async def _get_assets(page: int=0, limit: int=100):
    return await get_objects('asset', limit, page, [])

@app.get("/assets/{id}")
# Purpose: return the specific asset detail
async def _get_asset(id: str):
    return await get_asset(id)

@app.get("/contracts")
# Purpose: return all the contracts I defined
async def _get_contracts(page: int=0, limit: int=100):
    return await get_objects('contract', limit, page)

@app.post("/kit/basic/create/http")
# Purpose: To create a basic KIT as a HTTP type asset
async def _create_basic_kit_http_asset(input: createHttpBasicKIT):
    # data reshaping
    data_dict = input.dict()
    url = data_dict.pop("url")
    data_dict["asset_type"] = 'http'
    data_dict["offerType"] = 'service' # this value needs to be service, otherwise, the dataspace cannot trigger data transfer
    return await create_http_asset(url, input.kit_name, input.method, input.request_type, data_dict)

@app.post("/kit/basic/create/aws")
# Purpose: To create a basic KIT as a amazons3 type asset
async def _create_basic_kit_amazon_asset(input: createAwsBasicKIT):
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

@app.delete("/assets/{id}")
# Purpose: To delete an asset
async def _delete_asset(id: str):
    return await delete_asset(id)

@app.post("/contract")
# Purpose: To create a contract definition with the target asset id
async def _create_contract(input: createContract):
    return await create_contract(input.contract_id, input.policy_id, input.asset_id)

@app.get("/policy/{id}")
# Purpose: To get the policy definition of the given id
async def _get_policy(id: str):
    return await get_policy(id)

@app.delete("/contract/{id}")
# Purpose: To delete the contract definition of the given id
async def _delete_contract(id: str):
    return await delete_contract(id)

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

@app.post("/http/transfer")
# Purpose: Return the negotiation id for an http type asset
async def _negotiate(input: httpTransferRequestData):
    if input.asset_type == 'http':
        return await http_transfer(input.connector_url, input.provider_id, input.policy, input.asset_id, input.payload, input.post_action)
    else:
        raise HTTPException(
            status_code = 422,
            detail="Asset type other than http is not implemented"
        )

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
