import sys, asyncio
sys.path.insert(0, '/home/kali/Desktop/MACHINE/backend')
from app.core.auth import create_access_token

# Mint token for our admin
token = create_access_token(
    user_id="b5149768-25e1-4c04-81e8-d846b56da9b3",
    role="admin",
    is_admin=True
)
print("Token:", token)

import urllib.request
req = urllib.request.Request("http://127.0.0.1:8000/api/v1/admin/employees", headers={"Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req) as response:
    import json
    employees = json.loads(response.read().decode())
    print("Employees:", employees)
    if employees:
        emp_id = employees[0]["id"]
        print(f"Testing delete on {emp_id}")
        del_req = urllib.request.Request(f"http://127.0.0.1:8000/api/v1/admin/employees/{emp_id}", headers={"Authorization": f"Bearer {token}"}, method="DELETE")
        try:
            with urllib.request.urlopen(del_req) as del_res:
                print("Delete Result:", del_res.status, del_res.read().decode())
        except urllib.error.HTTPError as e:
            print("Delete Failed:", e.code, e.reason, e.read().decode())
