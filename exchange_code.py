"""Paste redirect URL as argument: python exchange_code.py "https://127.0.0.1/?code=..."  """
import base64, json, time, sys, httpx, os
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv('SCHWAB_CLIENT_ID')
CLIENT_SECRET = os.getenv('SCHWAB_CLIENT_SECRET')
CALLBACK_URL = os.getenv('SCHWAB_CALLBACK_URL')
TOKEN_PATH = Path(os.getenv('SCHWAB_TOKEN_PATH', '~/.schwab-mcp/token.json')).expanduser()

auth_code = parse_qs(urlparse(sys.argv[1]).query)['code'][0]
encoded = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()

r = httpx.post('https://api.schwabapi.com/v1/oauth/token',
    headers={'Authorization': f'Basic {encoded}', 'Content-Type': 'application/x-www-form-urlencoded'},
    data={'grant_type': 'authorization_code', 'code': auth_code, 'redirect_uri': CALLBACK_URL})

if r.status_code == 200:
    d = r.json()
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump({'access_token': d['access_token'], 'refresh_token': d['refresh_token'],
               'expires_at': time.time() + d['expires_in'], 'token_type': 'Bearer'}, open(TOKEN_PATH, 'w'), indent=2)
    print(f'Success! Token saved to {TOKEN_PATH}')
else:
    print(f'Error {r.status_code}: {r.text}')
