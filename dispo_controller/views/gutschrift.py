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

logger = logging.getLogger(__name__)

api_client = ApiClient()

months = [
    (1, 'Januar'),
    (2, 'Februar'),
    (3, 'März'),
    (4, 'April'),
    (5, 'Mai'),
    (6, 'Juni'),
    (7, 'Juli'),
    (8, 'August'),
    (9, 'September'),
    (10, 'Oktober'),
    (11, 'November'),
    (12, 'Dezember'),
]

corr_month_env = int(os.getenv('CORR_MONTH'))
CORR_MONTH = corr_month_env if corr_month_env else 0
COMPOSER_HOST = os.getenv('COMPOSER_HOST')

# Create your views here.
@api_view(['GET', 'POST'])
def test(request):
    return Response("OK")

# Gutschrift erstellen
# @api_view(['GET', 'POST'])
# def create_credit(request):
#     data = request.data
#     type = data["type"]
#     results = api_client.fetch(service="bez_database", resource="bez_disposition", params={"where": f"StateID=3|SupplierID={data['supplier']}|SiteID={data['site']}", "take": "2000"})
#     return Response("OK")

# Gutschrift erstellen
@api_view(['GET', 'POST'])
def create_credit(request):
    logger.info("Start composing invoices ...")
    result = None
    data = request.data
    type = data["type"]

    if type == "Gutschrift":
        results = api_client.fetch(service="bez_database", resource="bez_disposition", params={"where": f"StateID=3|SupplierID={data['supplier']}|SiteID={data['site']}", "take": "2000"})
        logger.info("Type: Gutschriften")
   
    # Fetch data from Dispo where StateID = 3
    if type == "Proforma":
        results = api_client.fetch(service="bez_database", resource="bez_disposition", params={"where": "StateID=3", "take": "20000"})
        logger.info("Type: Proforma")

    if results == None:
        return Response({
            "body": False
        })
    
    # Get actual month
    month_now = datetime.now().month - CORR_MONTH

  
    # Filter Data of actual month
    results_this_month = []
    for result in results:
        weighingdate = parser.parse(result["WeighingDate"])
        if weighingdate.month == month_now:
            results_this_month.append(result)

    
    # get coresponding threshold from price table
    results_this_month = resolve_threshold(results_this_month)
    
    # Rise alert if there are more data 
    if len(results) > len(results_this_month):
        diff = abs(len(results) - len(results_this_month))
        print(f"Es sind {diff} Buchungen von einem Anderen Monat offen")
        logger.info(f"Es sind {diff} Buchungen von einem Anderen Monat offen")
    
    # Group data by Supplier
    def key_func_supplier(k):
        return k['SupplierID']['name']
    
    sorted_result = sorted(results_this_month, key=key_func_supplier)
    sorted_items = []
    for key, value in groupby(sorted_result, key_func_supplier):
        sorted_items.append({
            key:list(value)
        })

    # Resolve data
    logger.info("Resolvong supplier data")
    for i,item in enumerate(sorted_items):
        values = item.values()
        for rows in values:
            resolved_rows = resolve_supplier(rows)
            sorted_items[i] = resolved_rows
    logger.info("Resolvong supplier data done")

    # Gpup by HKW
    def key_func_site(k):
        return k['SiteID']['name']
    
    sorted_items_site = []
    for sorted_item in sorted_items:
        result = sorted(sorted_item, key=key_func_site)
        for key, value in groupby(result, key_func_site):
            sorted_items_site.append({
                key:list(value)
            })
    
    for i,sorted_item_site in enumerate(sorted_items_site):
        values = sorted_item_site.values()
        for value in values:
            sorted_items_site[i] = value

    # Create table models
    table_models = []
    for sorted_item_site in sorted_items_site:
        table_models.append(get_tabel_model(sorted_item_site, request.data))
 
    #clean accounting data of actual month and insert new one
    if type == "Proforma":
        logger.info("Clean up old proforma....")
        cleanup_accounting_data()
        logger.info("Clean up old proforma done")

    model_count = len(table_models)
    for i,table_model in enumerate(table_models):
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(f"{COMPOSER_HOST}/invoice/get_invoice", data=json.dumps(table_model), headers=headers)
        with open(f'tmp2/{table_model["supplier"]}_{table_model["site_name"]}.pdf', 'wb') as f:
            f.write(response.content)
        write_to_dimetrics(
            data=request.data,
            content=response.content, 
            file_name=f'{table_model["supplier"]}_{table_model["site_name"]}.pdf', 
            proforma=True,
            supplier_id=table_model["supplier_id"],
            site_id=table_model["site_id"],
            results=results
            )
        #print(f'--> {table_model["supplier"]}_{table_model["site_name"]}.pdf | {i+1}/{model_count}')
        logger.info(f'--> {table_model["supplier"]}_{table_model["site_name"]}.pdf | {i+1}/{model_count}')

    return Response(table_models)



def resolve_supplier(rows):
    supplier_id = rows[0]["SupplierID"]["id"]
    supplier_data = api_client.get(service="bez_database", resource="bez_business_partner", id=supplier_id)
    for i,row in enumerate(rows):
        rows[i]["SupplierID"] = supplier_data
        # print(rows[i]["SiteID"]["name"])
        logger.info(rows[i]["SiteID"]["name"])
    
    return rows

 

def get_tabel_model(items, data):
    table_model = []
    user_name = data.get("user_name_prop")
    
    grouped = group_categories(items)
    sum_price = 0
    for entities in grouped:

        table_model.append(
                [
                    {
                        'name': 'Material',
                        'value': entities["MaterialID"]["name"],
                        'subtitle': '[Kategorie]'
                    },
                    {
                        'name': 'Wasser',
                        'value': entities.get("Water"),
                        'subtitle': '[% t-lutro]'
                    },
                    {
                        'name': 'Menge',
                        'value': str(dec((entities["Weight"]/1000))).replace('.', ','),
                        'subtitle': '[t-atro]'
                    },
                    {
                        'name': 'Preis',
                        'value': f"€ {str(dec(entities['Price'])).replace('.', ',')}",
                        'subtitle': '[€/t-atro]'
                    },
                    {
                        'name': 'Gesamt',
                        'value': f"€ {str(dec((entities['Weight']/1000)*entities['Price'])).replace('.', ',')}",
                        'subtitle': '[€/Kategorie]'
                    }
                ]
            )
        sum_price = dec(sum_price) + (dec((entities['Weight']/1000))*dec(entities['Price']))
        
    # create sum
    
    vat = (items[0]["SupplierID"]["VAT"]) * 10
    price_with_vat = sum_price * dec(vat) if sum_price * dec(vat) > 0 else 0
    sum_price = dec(sum_price + price_with_vat)
    vat_price = price_with_vat - sum_price if vat > 0 else 0

    table_model.append([
            {
                'name': 'Material',
                'value': f'zuzüglich {vat * 10} % MWSt'
            },
            {
                'name': 'Wasser',
                'value': ' '
            },
            {
                'name': 'Menge',
                'value': ''
            },
            {
                'name': 'Preis',
                'value': ' '
            },
            {
                'name': 'Gesamt',
                'value': f"€ {str(vat_price).replace('.', ',')}"
            }
        ])

    table_model.append([
            {
                'name': 'Gesamt',
                'value': 'Gesamt'
            },
            {
                'name': 'Wasser',
                'value': ' '
            },
            {
                'name': 'Menge',
                'value': ''
            },
            {
                'name': 'Preis',
                'value': ' '
            },
            {
                'name': 'Summe',
                'value': f"€ {str(sum_price).replace('.', ',')}"
            }
        ])

    return {
        "type": data.get("type"),
        "billnr":data.get("billnr"),
        "supplier" : items[0]["SupplierID"]["Name"],
        "supplier_street" : items[0]["SupplierID"]["Street"],
        "supplier_city" : items[0]["SupplierID"]["CityID"]["name"],
        "create_date" : str(datetime.now().date()),
        "uid" : items[0]["SupplierID"]["UID"],
        "supplier" : items[0]["SupplierID"]["Name"],
        "month" : months[datetime.now().month - CORR_MONTH -1][1],
        "user_name": user_name,
        "site_name" : items[0]["SiteID"]["name"],
        "site_street" : data.get("site_street"),
        "site_city" : data.get("site_city"),
        "pay_target" : items[0]["SupplierID"]["PaymentDays"],
        "iban" : items[0]["SupplierID"]["IBAN"],
        "bic" : items[0]["SupplierID"]["BIC"],
        "company_name" : data.get("company_name"),
        "company_street" : data.get("company_street"),
        "company_city" : data.get("company_city"),
        "company_plz" : data.get("company_plz"),
        "company_fb" : data.get("company_fb"),
        "company_uid" : data.get("company_uid"),
        "company_tel" : data.get("company_tel"),
        "company_fax" : data.get("company_fax"),
        "company_mail" : data.get("company_mail"),
        "company_bank_name" : data.get("company_bank_name"),
        "company_iban" : data.get("company_iban"),
        "company_bic" : data.get("company_bic"),
        "table_model" : table_model,
        "supplier_id": items[0]["SupplierID"]["id"],
        "site_id": items[0]["SiteID"]["id"]
    }

def group_categories(items):
    def key_func_water(k):
        return k['Water']
    
    sorted_result = sorted(items, key=key_func_water)
    sorted_items_ = []
    for key, value in groupby(sorted_result, key_func_water):
        sorted_items_.append({
            key:list(value)
        }) 
    
    for i,sorted_item in enumerate(sorted_items_):
        values = sorted_item.values()
        for value in values:
            sorted_items_[i] = value

    # sort by Material
    def key_func(k):
        return k['MaterialID']['name']
    
    new_sorted_items = []

    for items in sorted_items_:
        sorted_result = sorted(items, key=key_func)
        sorted_items = []
        for key, value in groupby(sorted_result, key_func):
            sorted_items.append({
                key:list(value)
            }) 
        
        for i,sorted_item in enumerate(sorted_items):
            values = sorted_item.values()
            for value in values:
                sorted_items[i] = value

        # aggregate material
        agg_sorted_items = []  
        def calc_weight(material_type_entrie):
            weight = material_type_entrie["Weight"] * (1-material_type_entrie["WeightCorrection"]) 
            return weight

        for i,material_type_entries in enumerate(sorted_items):
            total_weight = sum([calc_weight(w) for w in material_type_entries])
            agg_entry = material_type_entries[0]
            agg_entry["Weight"] = total_weight
            sorted_items[i] = agg_entry

        print("---")
        new_sorted_items.append(sorted_items)
     
    res = []
    for new_sorted_item in new_sorted_items:
        for new_sorted_item_ in new_sorted_item:
            res.append(new_sorted_item_)

    return res 
 


def write_to_dimetrics(data, supplier_id, site_id, content=None, file_name="file", proforma=True, results=None):
    
    encoded = None
    if content:
        encoded = base64.b64encode(content)
        encoded = encoded.decode("utf-8")
    
    if data["type"] == "Proforma":
        results = api_client.fetch(service="bez_database", resource="bez_accounting", params={"take": "1", "order_by": "AccountingNumber"})
        last_accounting = results[0] 
        accounting_number = last_accounting.get("AccountingNumber")
        
        next_acc_year = datetime.now().year
        next_acc_month = f"{datetime.now().month:02d}" 
        next_acc_index = f"{(next_index(last_accounting)):04d}"
        next_acc_nr = f"{next_acc_year}{next_acc_month}{next_acc_index}"

        file_name = next_acc_nr + "_" + file_name
 
    actual_month = datetime.now(tz=pytz.timezone('Europe/Vienna')).month


    if data["type"] == "Proforma":
        data_obj = {
            "AccountingNumber": next_acc_nr,
            "ClosedDate": datetime.now(tz=pytz.timezone('Europe/Vienna')).replace(month=actual_month - CORR_MONTH).strftime('%Y-%m-%d %H:%M:%S'),
            "booked": False,
            "supplier": supplier_id,
            "site": site_id,
            "proforma":[
                {
                    "name": file_name,
                    "content": encoded
                } 
            ]
        } 
 
    if data["type"] == "Gutschrift":
        data_obj = {
            "AccountingNumber": data["billnr"],
            "ClosedDate": datetime.now(tz=pytz.timezone('Europe/Vienna')).replace(month=actual_month - CORR_MONTH).strftime('%Y-%m-%d %H:%M:%S'),
            "booked": True,
            "credit":[
                {
                    "name": file_name,
                    "content": encoded
                } 
            ]
        } 

    if data["type"] == "Proforma":
        response = api_client.post(service="bez_database", resource="bez_accounting", data=data_obj)
        
    
    if data["type"] == "Gutschrift":
        response = api_client.update(service="bez_database", resource="bez_accounting", data=data_obj, id=data["id"], callback=set_dispo_status, results=results)
        print(response)
        
    
    # result = api_client.get(service="genservice1", resource="persons2_sql", id=2)
    # result = api_client.post(service="genservice1", resource="persons2_sql", data={"name": "Daniel"})
    # result = api_client.update(service="genservice1", resource="persons2_sql", data={"name": "DanielF"}, id=14)
    # result = api_client.delete(service="genservice1", resource="persons2_sql", id=14)


def set_dispo_status(response, results):
    if response.ok:
        for dispo_obj in results:
            accounting_obj = response.json()
            data_obj = {"StateID": 4, "AccountingID": accounting_obj["id"]}
            r = api_client.update(service="bez_database", resource="bez_disposition", data=data_obj, id=dispo_obj["id"])
            print(f"Dispo: {r['id']} set to close") 
    else:
        print("ERROR") 
    
 
def next_index(last_accounting):
    accounting_number = last_accounting.get("AccountingNumber")
    acc_nr_year = int(accounting_number[:4])
    acc_nr_index = int(accounting_number[6:])
    next_acc_year = datetime.now().year

    if(next_acc_year > acc_nr_year):
        return 1   
    return acc_nr_index + 1

def cleanup_accounting_data():
    #ClosedDate%3D2021-08-01T00:00:00.000Z--2021-08-31T23:59:59.999Z
    given_date = datetime.now(tz=pytz.timezone('Europe/Vienna')).replace(hour=0, minute=0, second=0)
    if CORR_MONTH > 0:
        given_date = given_date.replace(month=given_date.month-CORR_MONTH)
    first_day_of_month = given_date.replace(day=1)

    last_day_of_month = given_date.replace(day = calendar.monthrange(given_date.year, given_date.month)[1])
    last_day_of_month = last_day_of_month.replace(hour=23, minute=59, second=59)

    first_day_of_month = first_day_of_month.strftime('%Y-%m-%d %H:%M:%S')
    last_day_of_month = last_day_of_month.strftime('%Y-%m-%d %H:%M:%S')

    results = api_client.fetch(service="bez_database", resource="bez_accounting", params={"where": f"ClosedDate={first_day_of_month}--{last_day_of_month}"})
    
    for result in results:
        response = api_client.delete(service="bez_database", resource="bez_accounting", id=result["id"])
        print(f"--> Deleted: {response}") 
        logger.info(f"--> Deleted: {response}")


def resolve_threshold(results):
    response = api_client.fetch(service="bez_database", resource="bez_price", params={"take": "10000000"})
    for i,result in enumerate(results): 
        weighting_date = parser.parse(result["WeighingDate"])
        # params={"where": f"DateEnd>={weighting_date}|SupplierID={result['SupplierID']['id']}|MaterialID={result['MaterialID']['id']}"}
        item = [r for r in response if r["SupplierID"]["id"] == result["SupplierID"]["id"] and r["MaterialID"]["id"] == result["MaterialID"]["id"] and parser.parse(r["DateEnd"]) >= weighting_date]
        if item != None:
            if len(item) > 1:
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            if len(item) > 0:
                item = item[0]
                th1 = dec(item["Threshold1"]) 
                th2 = dec(item["Threshold1"])
                wc = result["WeightCorrection"]
                water = None
                if wc >= th1:
                    water = f">{th1*100}"
                if wc <= th1:
                    water = f"<{th1*100}"
                if wc >= th2:
                    water = f">{th2*100}"
                if wc <= th2:
                    water = f"<{th2*100}"
                
                results[i]["Water"] = water
    return results


        