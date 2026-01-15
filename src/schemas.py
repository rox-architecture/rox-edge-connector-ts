from pydantic import BaseModel, Field
from typing import Literal, Any

# Done
class createAwsBasicKIT(BaseModel): 
    # General Information
    asset_name: str = Field(..., min_length=1)   # must not be empty
    version: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    tag: str | None = None
    business: str | None = None
    vision: str | None = None
    license: str | None = None

    # bucket information
    storage_url: str
    bucket_name: str
    storage_region: str
    storage_username: str
    storage_password: str
    object_path: str

    # semantic model
    semantic_model: dict = Field(..., min_length=1)
    icon: str | None = None

# Done
class createHttpBasicKIT(BaseModel): # Used to create an HTTP Basic KIT
    # General Information
    kit_name: str = Field(..., min_length=1)   # must not be empty
    kit_type: str = Literal["basic", "composite"]
    version: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    tag: str | None = None
    business: str | None = None
    vision: str | None = None
    license: str | None = None
    contact: str | None = None
    
    # Asset location information
    url: str = Field(..., min_length=1)
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    request_type: Literal["none", "application/json", "multipart/form-data", "application/octet-stream"]
    request_body: dict | None = None

    # semantic model
    semantic_model: dict = Field(..., min_length=1)
    icon: str | None = None

    offerType: Literal["data", "service"]
    default_file_name: str | None = None
    default_postprocessing: str | None = None
    header: str | None = None

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


class AwsTransferRequestBody(BaseModel):
    provider_id: str
    asset_id: str
    catalog_url: str
    # minio information
    minio_url: str
    minio_username: str
    minio_password: str
    minio_bucket: str
    minio_region: str

class HttpTransferRequestBody(BaseModel):
    provider_id: str
    asset_id: str
    catalog_url: str | None = None
    # downloaded file
    filename: str | None = None
    payload: str | None = None

class SearchFormat(BaseModel):
    object_type: str
    query: str