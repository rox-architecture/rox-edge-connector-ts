# Edge Connector

The edge-connector aims to bridge between the local robot software and dataspace.
It consists of automation functionalities to remove manual tasks in AI-robot software deployment.

# Getting started

*Important: disconnect from DLR VPN otherwise some parts may not work.

Depending on what you want to do with the edge-connector, select either Case 1 or Case 2 below. Both methods will run the edge-connector, but with or without using Docker.

## Case 1: For development

If you want to extend the edge-connector features, and if you don't need to run everything together (e.g., Airflow), then you can simply run only the edge-connector:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
To check, access `http://localhost:8000/` in your browser. You should see a welcome message.
You can also check `http://localhost:8000/docs` for API references.

## Case 2: For system integration

For the production and software packaging, we eventually want to run the edge-connector in a container. 

Build and run the edge-connector container.
```bash
docker-compose build
docker-compose up
``` 
To check, access `http://localhost:8000/` in your browser. You should see a welcome message.
You can also check `http://localhost:8000/docs` for API references.

## Providing your certificates

Either Case 1 or Case 2, you will have to provide your dataspace certificates to enable interaction with the dataspace. 
Download your certificates from DLR dataspace. Go to [https://vision-x-dataspace.base-x-ecosystem.org/](https://vision-x-dataspace.base-x-ecosystem.org/) and login. Then download the certificate by clicking the button on the top-right menu. We will need `tls.crt` and `tls.key` files. Also, setup your connector if you didn't. We will need the connector name.

We add the certificate to the edge-connector. Make sure that edge connector is running.

Enter the below command in the location where you unzipped the certificate files. Replace `jinwooro` with your own user name and `conn_jin` with your connnector name. You will see the response telling that the certificate files are registered.
```bash
curl -X POST http://localhost:8000/register/dlr/dataspace \
  -F "tls_crt=@tls.crt" \
  -F "tls_key=@tls.key" \
  -F "username=jinwooro" \
  -F "conn_name=conn_jin"
```
To check, access `http://localhost:8000/dlr/token` in your browser. You should be able to see a token from the DLR dataspace.

Now, the setup is done!! You can explore APIs.

A Postman workspace is also setup for testing all the existing endpoints. It is located in the collection folder.

# API references

When the Edge Connector is running, use a browser to access:
```bash
http://localhost:8000/docs
```

# Resources

- See the DLR dataspace API documentation at [here](https://docs.adsel.space/home/)
- DLR dataspace UI at [here](https://vision-x-dataspace.base-x-ecosystem.org/)
- Tractus-X EDC API at [here](https://eclipse-tractusx.github.io/tractusx-edc/openapi/control-plane-api/#/)
- MinIO is set by default the data source and sink for DLR dataspace operations, which is at [here](https://vision-x-dataspace.base-x-ecosystem.org/)



