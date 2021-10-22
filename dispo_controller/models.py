from datetime import datetime
from django.db import models

from bedb_mw.services.dmx_api_client import ApiClient
import json
from dateutil import parser


# Create your models here.

api_client = ApiClient()

class ContractModel():
    def __init__(self, data) -> None:
        self.contract_start = parser.parse(data['contract_start'])
        self.contract_end = parser.parse(data["contract_start"])
        self.supplier = Supplier(data['supplier']['id'])
        self.supplier_conditions = data['supplier_conditions']
        self.supplier_general_conditions = data['supplier_general_conditions']
        self.hkw_ost = data['hkw_ost']
        self.hkw_sud = data['hkw_sud']
        self.hkw_nord = data['hkw_nord']
        self.material = data['material']
        self.threshold1 = data['threshold1']
        self.threshold2 = data['threshold2']
        self.origin = data['origin']
        self.freigegeben = data['freigegeben']
        self.id = data['id']
        self.supplier_prices = self.resolve_supplier_prices()
        self.supplier_amounts = self.resolve_supplier_amounts()
        
        super().__init__()

    def resolve_supplier(self, id):
        return api_client.get(
            service="bez_database",
            resource="bez_business_partner",
            id=id
        )

    def resolve_supplier_amounts(self):
        resp = api_client.fetch(
            service="bez_database",
            resource="bez_order_amount",
            params={
                "take": "1000",
                "where": f"contract={self.id}"
            }
        )
        resp = [SupplierAmount(r) for r in resp]
        return resp

    def resolve_supplier_prices(self) -> list:
        resp = api_client.fetch(
            service="bez_database",
            resource="bez_order_price",
            params={
                "take": "1000",
                "where": f"contract={self.id}"
            }
        )
        resp = [SupplierContractPrices(r) for r in resp]
        return resp

class Material:
    name: str
    code: str
    heat_value: float
    ash: float
    conversion_srm: float
    conversion_fm: float
    ingest_timestamp: None
    id: int

    def __init__(self, data) -> None:
        self.name = data.get("name")
        self.code = data.get("code")
        self.heat_value = data.get("heat_value")
        self.ash = data.get("ash")
        self.conversion_srm = data.get("conversion_srm")
        self.conversion_fm = data.get("conversion_fm")
        self.id = data.get("id")

class SupplierContractPrices:
    ame: str
    price_1: float
    price_2: float
    price_3: float
    material: Material
    orderdate_start: datetime
    orderdate_end: datetime
    min_amout: float
    max_amount: float
    id: int

    def __init__(self, data) -> None:
        self.name = ("name")
        self.price_1 = data.get("price_1")
        self.price_2 = data.get("price_2")
        self.price_3 = data.get("price_3")
        self.material = self.resolve_material(data['material']['id'])
        self.orderdate_start = parser.parse(data.get("orderdate_start"))
        self.orderdate_end = parser.parse(data.get("orderdate_end"))
        self.min_amout = data.get("min_amout")
        self.max_amount = data.get("max_amount")
        self.id = data.get("id")

    def resolve_material(self, id):
        return api_client.get(
            service="bez_database",
            resource="bez_material",
            id=id
        )

class SupplierAmount:
    name: str    
    order_start: datetime
    order_end: datetime
    min_order: float
    max_order: float
    material: Material
    id: int

    def __init__(self, data) -> None:
        self.name = data.get("name")
        self.order_start = parser.parse(data.get("order_start"))
        self.order_end = parser.parse(data.get("order_end"))
        self.min_order = data.get("min_order")
        self.max_order = data.get("max_order")
        self.material = self.resolve_material(data["material"]["id"])
        self.id = data.get("id")

    def resolve_material(self, id):
        return api_client.get(
            service="bez_database",
            resource="bez_material",
            id=id
        )


class Supplier:
    name: str
    street: str
    street_number: int
    email: str
    telephone: str
    contact_person: str
    vat: float
    uid: str
    iban: str
    bic: str
    payment_days: int
    payment_net: bool
    testing: bool
    comment: str
    id: int

    def __init__(self, id) -> None:
        data = self.resolve(id)
        self.name = data.get("name")
        self.street = data.get("street")
        self.street_number = data.get("street_number")
        self.city_id = data.get("city_id")
        self.email = data.get("email")
        self.telephone = data.get("telephone")
        self.contact_person = data.get("contact_person")
        self.vat = data.get("vat")
        self.uid = data.get("uid")
        self.iban = data.get("iban")
        self.bic = data.get("bic")
        self.payment_days = data.get("payment_days")
        self.payment_net = data.get("payment_net")
        self.testing = data.get("testing")
        self.comment = data.get("comment")
        self.state_id = data.get("state_id")
        self.reseller = data.get("reseller")
        self.customer = data.get("customer")
        self.creator = data.get("creator")
        self.id = data.get("id")

    def resolve(self, id):
        return api_client.get(
            service="bez_database",
            resource="bez_business_partner",
            id=id
        )