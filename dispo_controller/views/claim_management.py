from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from bedb_mw.services.dmx_api_client import ApiClient

client = ApiClient()

@api_view(['GET', 'POST'])
def create_claim(request):
    data = request.data
    print(data)
    files = get_files(data)
    request_data = {
            "name": data["name"],
            "reason_selected": int(data["reason_selected"]) if data.get("reason_selected") else None,
            "disposition": int(data["disposition"]),
            "reason": data.get("reason") or " ",
            "files": files if len(files) > 0 else None
        }
    client.post(
        service="bez_database",
        resource="bez_claim_management",
        data=request_data,
        callback=set_claim
    )

    return Response(status = status.HTTP_200_OK)

def get_files(data):
    files = []
    for i in range(6):
        try:
            files.append({
                "name": data["files_name" + str(i)],
                "content": data["files"+str(i)]
            })
        except:
            pass
    return files

def set_claim(response):
    if response.ok:
        data = response.json()
        client.update(
            service="bez_database",
            resource="bez_disposition",
            data={
                "StateID": 6
            },
            id=data['disposition']['id']
        )
        