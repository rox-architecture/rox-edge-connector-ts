# Edge-Connector

`Edge-Connector` is a small server running on your local system to provide the following services:
- Ensure that your input data are correctly in the KIT format.
- 

## To Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

To check, access `http://localhost:8001/` in your browser. You should see a welcome message.
You can also check `http://localhost:8000/docs` for API references.

## Providing your certificates

`Edge-Connector` need your dataspace user certificate files in the working directory.
This can be done by using the `KIT GUI` frontend or manually. 
How to use the frontend is explained in the `KIT GUI` repository.
For doing it manually, go to [https://vision-x-dataspace.base-x-ecosystem.org/](https://vision-x-dataspace.base-x-ecosystem.org/) and login.
Then download the certificate by clicking the button on the top-right menu. We will need `tls.crt` and `tls.key` files.
Place them in the `Edge-Connector` directory (i.e., next to the main.py file).

Then, you need to set your connector name in `.env` file. 
For example, `CONNECTOR_NAME=jin-conn`, replace `jin-conn` with your connector name.

To check everything works good, access http://localhost:8001/livecheck in your browser.
If you see a token value, then it means working good.

# Resources

- See the DLR dataspace API documentation at [here](https://docs.adsel.space/home/)
- DLR dataspace UI at [here](https://vision-x-dataspace.base-x-ecosystem.org/)
- Tractus-X EDC API at [here](https://eclipse-tractusx.github.io/tractusx-edc/openapi/control-plane-api/#/)



