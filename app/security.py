import os, json, base64, hmac, hashlib, secrets, time
from datetime import timedelta

SECRET_KEY=os.getenv('SECRET_KEY','dev-secret-change-me').encode()
ACCESS_TOKEN_MINUTES=int(os.getenv('ACCESS_TOKEN_MINUTES','720'))

def _b64e(b:bytes)->str:
    return base64.urlsafe_b64encode(b).decode().rstrip('=')

def _b64d(s:str)->bytes:
    return base64.urlsafe_b64decode(s + '='*((4-len(s)%4)%4))

def hash_password(password:str)->str:
    salt=secrets.token_bytes(16)
    iterations=260000
    dk=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,iterations)
    return f'pbkdf2_sha256${iterations}${_b64e(salt)}${_b64e(dk)}'

def verify_password(password:str,stored:str)->bool:
    try:
        scheme,it,salt_s,hash_s=stored.split('$',3)
        if scheme!='pbkdf2_sha256': return False
        salt=_b64d(salt_s); expected=_b64d(hash_s)
        actual=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,int(it))
        return hmac.compare_digest(actual,expected)
    except Exception:
        return False

def create_token(data:dict)->str:
    payload=data.copy(); payload['exp']=int(time.time())+ACCESS_TOKEN_MINUTES*60
    raw=json.dumps(payload,separators=(',',':'),sort_keys=True).encode()
    p=_b64e(raw)
    sig=_b64e(hmac.new(SECRET_KEY,p.encode(),hashlib.sha256).digest())
    return p+'.'+sig

def decode_token(token:str)->dict:
    p,sig=token.split('.',1)
    expected=_b64e(hmac.new(SECRET_KEY,p.encode(),hashlib.sha256).digest())
    if not hmac.compare_digest(sig,expected): raise ValueError('invalid signature')
    data=json.loads(_b64d(p))
    if int(data.get('exp',0))<int(time.time()): raise ValueError('expired')
    return data
