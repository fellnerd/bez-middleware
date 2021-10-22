from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status

from bedb_mw.services.dmx_api_client import ApiClient
from dateutil import parser


client = ApiClient()

@api_view(['GET', 'POST'])
def create_supplier_amount_ref(request):
    identifier = request.data["identifier"]

    response = client.get(
        service="bez_database",
        resource="bez_order_amount",
        id=identifier
    )

    min_date = parser.parse(response["order_start"])
    max_date = parser.parse(response["order_end"])
    name = response["contract"]["name"]
    res = f"{name}{min_date.month}{min_date.year}-{max_date.month}{max_date.year}"

    return Response(res)
