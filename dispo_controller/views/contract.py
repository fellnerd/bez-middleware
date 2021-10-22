from bedb_mw.services.helpers import dec
import requests
from bedb_mw.services.dmx_api_client import ApiClient
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from datetime import datetime
from dateutil import parser
from collections import defaultdict
from itertools import groupby
import json
from decimal import Decimal
import base64
import pytz
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import os
import logging

from dispo_controller.models import ContractModel

logger = logging.getLogger(__name__)

api_client = ApiClient()

COMPOSER_HOST = os.getenv('COMPOSER_HOST')

# Vertrag erstellen
@api_view(['GET', 'POST'])
def create_contract(request):
    logger.info("Start composing invoices ...")
    request_identifier = request.data["request_identifier"]
    contract_data = api_client.get(
        service="bez_database",
        resource="bez_contract",
        id=request_identifier
    )
    # contract_instance = ContractModel(contract_data)



    contract_data["supplier"] = api_client.get(
        service="bez_database",
        resource="bez_business_partner",
        id=contract_data["supplier"]["id"]
    )

    contract_data["order_price"] = api_client.fetch(
            service="bez_database",
            resource="bez_order_price",
            params={
                "take": "1000",
                "where": f"contract={contract_data['id']}"
            }
        )

    contract_data['order_amount'] = api_client.fetch(
            service="bez_database",
            resource="bez_order_amount",
            params={
                "take": "1000",
                "where": f"contract={contract_data['id']}"
            }
        )

    for i,order_amount in enumerate(contract_data['order_amount']):
        res = api_client.get(
            service="bez_database",
            resource="bez_material",
            id=order_amount["material"]["id"]
        )
        contract_data['order_amount'][i]["material"] = res


    for i,order_price in enumerate(contract_data['order_price']):
        res = api_client.get(
            service="bez_database",
            resource="bez_material",
            id=order_price["material"]["id"]
        )
        contract_data['order_price'][i]["material"] = res

    # contract_data["material"] = api_client.get(
    #     service="bez_database",
    #     resource="bez_material",
    #     id=contract_data["material"]["id"]
    # )

    
    if contract_data["freigegeben"] == False:
        headers = {"Content-Type": "application/json"}
        response = requests.post(f"{COMPOSER_HOST}/invoice/contract", data=json.dumps(contract_data), headers=headers)
        with open(f'tmp_contracts/contract.pdf', 'wb') as f:
                f.write(response.content)
        write_to_dimetrics(content = response.content, identifier=request_identifier, name=contract_data.get("name"))
    else:
        ### Vertrag wurde freigegeben -> Preise erstellen
        if not contract_data["preise_erstellt"]:
            create_prices(contract_data)
            create_stock(contract_data)
    

    return Response(contract_data)

def write_to_dimetrics(content=None, identifier=None, name="Vertrag"):
    encoded = None
    if content:
        encoded = base64.b64encode(content)
        encoded = encoded.decode("utf-8")

    api_client.update(
        service="bez_database",
        resource="bez_contract",
        id=identifier,
        data={
            "contract":[
                {
                    "name": f"{name}.pdf",
                    "content": encoded
                }
            ]
        }
    )

def create_prices(contract):

    for price in contract["order_price"]:
        logging.info(f"Preis wird erstellt für Vertrag <{contract['name']}>:")
        result = api_client.post(
            service="bez_database",
            resource="bez_price",
            data={
                "Price1": price["price_1"],
                "Price2": price["price_2"],
                "Price3": price["price_3"],
                "Threshold1": contract['threshold1']/100,
                "Threshold2": contract['threshold2']/100,
                "name": contract["name"],
                "MaterialID": price["material"]["id"],
                "SupplierID": contract["supplier"]["id"],
                "StateID": 3,
                "DateStart": contract['contract_start'],
                "DateEnd": contract['contract_end']
            }
        )

### erstellt einen bestellung für jede Einzelposition im Vertrag
def create_stock(contract):
    stocks = contract["order_amount"]
    for stock in stocks:
        min_order_date = parser.parse(stock["order_start"])
        max_order_date = parser.parse(stock["order_end"])
        timeframes = split_timeframe(min_order_date, max_order_date)
        for timeframe in timeframes:
            api_client.post(
                service="bez_database",
                resource="bez_ordersystem_stock",
                data={
                    "name": stock["name"],
                    "material": stock["material"]["id"],
                    "order_start": timeframe["min"],
                    "order_end": timeframe["max"],
                    "min_order": stock["min_order"],
                    "max_order": stock["max_order"],
                    "supplier": contract["supplier"]["id"]

                }
            )

def split_timeframe(min_order_date, max_order_date):
    pass
