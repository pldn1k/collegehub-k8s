import requests
import json

resp = requests.post('http://localhost:8000/api/auth/login', 
                     json={'username':'student1','password':'pass123'})
token = resp.json()['token']

resp2 = requests.get('http://localhost:8000/api/auth/verify',
                     headers={'Authorization': f'Bearer {token}'})
print('User data from verify:')
print(json.dumps(resp2.json(), indent=2, ensure_ascii=False))
