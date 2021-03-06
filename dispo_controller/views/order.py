from datetime import datetime
from requests.api import request
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
import pytz
import requests
from bedb_mw.services.dmx_api_client import ApiClient
from dateutil import parser
import json
client = ApiClient()

@api_view(['GET', 'POST'])
def make_order(request):
    data = request.data
    order = client.get(
        service="bez_database",
        resource="bez_ordersystem",
        id=data["identifier"]
    )

    try:
        order["stock"] = client.get(
            service="bez_database",
            resource="bez_ordersystem_stock",
            id=order["stock"]["id"]
        )

        order["stock"]["supplier"] = client.get(
            service="bez_database",
            resource="bez_business_partner",
            id=order["stock"]["supplier"]["id"]
        )

        ### Get template
        template_data = client.get(
            service="bez_settings",
            resource="bez_mail_templates",
            id=1
        )

        ### subtract by amount
        refresh_stock(order)

        ### send mail to supplier
        order_min_data = parser.parse(order['order_start_date'])
        order_max_data = parser.parse(order['order_date_end'])
        receiver = order['stock']['supplier']['Email']
        status_sent = send_mail(
            order=order,
            template=template_data["template"],
            message=f"""
            Sehr geehrter Geschäftspartner!

            Für die kommende Woche bestellen wir hiermit bei Ihnen folgende Waldhackgutlieferungen:
            
            Lieferzeitraum: {order_min_data.day}.{order_min_data.month}.{order_min_data.year} bis {order_max_data.day}.{order_max_data.month}.{order_max_data.year}
            <strong><span style="font-size: 20px;">{order['amount']}</span></strong> LKW <strong>{order['stock']['material']['name']}</strong>
            für das Werk: <strong>{order['site']['name']}</strong>

            * 1 LKW = ca. 12-16 t atro

            <strong>Bitte beachten Sie unsere aktuellen Anlieferzeiten:</strong>
            """,
            message_header=f"Bestellung von {order['stock']['material']['name']}",
            receiver="dfellner@anexia-it.com",
            subject=f"Bestellung von {order['stock']['material']['name']}"
        )
        if status_sent:
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        try:
            err = str(e)
            if err:
                err = err.replace("'", "")
            client.update(
                service="bez_database",
                resource="bez_ordersystem",
                data={
                    "error": err,
                },
                id=order['id']
            )
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def refresh_stock(order):
    min_order = order["stock"]["min_order"] - order["amount"]
    max_order = order["stock"]["max_order"] - order["amount"]

    client.update(
        service="bez_database",
        resource="bez_ordersystem_stock",
        id=order["stock"]["id"],
        data={
            "min_order": min_order,
            "max_order": max_order
        }
    )

def send_mail(order, template, receiver, subject, message_header = "", message = ""):
    data = {
            "template":template,
            "sender_mail":"system@dimetrics.io",
            "password":"Felldl1304#",
            "port":"465",
            "sender_name":"Dimetrics",
            "smtp_addr":"dimetrics.io",
            "user":"system@dimetrics.io",
            "subject": subject,
            "message": message,
            "receiver_email": receiver,
            "message_header": message_header,
            "company_meta": "Bioenergiezentrum GmbH",
            "html_message": False
        }
    response = requests.post(
        url="https://dimetrics-func.azurewebsites.net/api/mailer?code=AB8UrAM5M7a/6qxj9osKMDpzKQ1fHrDfgRa/7PDVMfA5n3cqPfcBww==",
        data=json.dumps(data),
        headers={"Content-Type": "application/json"}
    )
    if response.ok:
        date_now = str(datetime.now(tz=pytz.timezone('Europe/Vienna')))
        client.update(
            service="bez_database",
            resource="bez_ordersystem",
            data={
                "sent": True,
                "order_date": date_now
                
            },
            id=order['id']
        )
        return True
    return False
    
