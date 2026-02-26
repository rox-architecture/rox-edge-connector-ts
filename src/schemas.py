from pydantic import BaseModel, Field
from typing import Literal, Any, List

# class createAwsBasicKIT(BaseModel): 
#     # General Information
#     asset_name: str = Field(..., min_length=1)   # must not be empty
#     version: str = Field(..., min_length=1)
#     description: str = Field(..., min_length=1)
#     tag: str | None = None
#     business: str | None = None
#     vision: str | None = None
#     license: str | None = None

#     # bucket information
#     storage_url: str
#     bucket_name: str
#     storage_region: str
#     storage_username: str
#     storage_password: str
#     object_path: str

#     # semantic model
#     semantic_model: dict = Field(..., min_length=1)
#     icon: str | None = None

class KitGeneralData(BaseModel): # General KIT data
    kit_name: str = Field(..., min_length=1)
    kit_type: Literal["basic", "composite"]
    version: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    offerType: Literal["data", "service"]
    tag: str | None = None
    business: str | None = None
    vision: str | None = None
    license: str | None = None
    contact: str | None = None
    standardisation: str | None = None
    domain: str | None = None

class HttpAccessData(BaseModel): # Access data for HTTP request
    asset_type: Literal["http"]
    url: str = Field(..., min_length=1)
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    request_type: str | None = None
    request_body: dict | None = None
    header: dict | None = None

class AdditionalData(BaseModel):
    execution_commands: str | None = None
    default_file_name: str | None = None
    icon: str | None = None

class BasicKitData(BaseModel):
    general_info: KitGeneralData
    access_info: HttpAccessData # | AwsAccessData  # for the future work
    semantic_model: dict = Field(..., min_length=1)
    additional_info: AdditionalData | None = None

class KitReference(BaseModel):
    provider_id: str
    kit_name: str
    read_policy_id: str | None = None 
    use_policy_id: str | None = None 

class CompositeKitData(BaseModel):
    general_info: KitGeneralData
    access_info: HttpAccessData # | AwsAccessData
    components: List[KitReference] | None = None
    semantic_model: dict = Field(..., min_length=1)
    additional_info: AdditionalData | None = None

class KitAccessRequest(BaseModel):
    provider_id: str = Field(..., min_length=1)
    connector_url: str = Field(..., min_length=1)
    kit_name: str = Field(..., min_length=1)
    request_body: dict | None = None
    overwrite: bool | None = None

class CatalogRequestData(BaseModel):
    provider_id: str
    connector_url: str
    kit_name: str | None = None
    
# Done
class createContract(BaseModel):
    contract_id : str
    policy_id: str
    asset_id: str

# Done
class httpTransferRequestData(BaseModel):
    provider_id: str = Field(..., min_length=1)
    connector_url: str = Field(..., min_length=1)
    asset_id: str = Field(..., min_length=1)
    policy: dict = Field(..., min_length=1)
    asset_type: Literal["http", "aws"]
    payload: dict | None = None
    post_action: dict | None = None

# Done
class editAssetData(BaseModel):
    context: dict = Field(..., min_length=1)
    asset_id: str
    properties: dict = Field(..., min_length=1)
    dataAddress: dict = Field(..., min_length=1)


class httpTransfer2url(BaseModel):
    originator: str = Field(..., min_length=1)
    agreement_id: str = Field(..., min_length=1)
    endpoint_url: str = Field(..., min_length=1)


# class createCompositeKIT(BaseModel):
#     # General Information
#     kit_name: str = Field(..., min_length=1)   # must not be empty
#     kit_type: str = Literal["composite"]
#     version: str = Field(..., min_length=1)
#     description: str = Field(..., min_length=1)
#     tag: str | None = None
#     business: str | None = None
#     vision: str | None = None
#     license: str | None = None
#     contact: str | None = None
#     standardisation: str | None = None
#     domain: str | None = None

#     # Asset location information
#     url: str = Field(..., min_length=1)
#     method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
#     request_type: Literal["none", "application/json", "multipart/form-data", "application/octet-stream"]
#     request_body: dict | None = None

#     # semantic model
#     semantic_model: dict = Field(..., min_length=1)
#     icon: str | None = None

#     offerType: Literal["data", "service"]
#     default_file_name: str | None = None
#     postprocessing_cmd: str | None = None
#     header: str | None = None    


# class AwsTransferRequestBody(BaseModel):
#     provider_id: str
#     asset_id: str
#     catalog_url: str
#     # minio information
#     minio_url: str
#     minio_username: str
#     minio_password: str
#     minio_bucket: str
#     minio_region: str

# class HttpTransferRequestBody(BaseModel):
#     provider_id: str
#     asset_id: str
#     catalog_url: str | None = None
#     # downloaded file
#     filename: str | None = None
#     payload: str | None = None

# class SearchFormat(BaseModel):
#     object_type: str
#     query: str