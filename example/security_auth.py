"""
Simple CRUD with custom JWT authentication using FlaskNova (no flask_jwt_extended)
"""
from flask import g, request, make_response, jsonify
from src.flask_nova import status
import time, hmac, hashlib, base64, json
from functools import wraps
SECRET = 'supersecretjwtkey'

# JWT helpers

def encode_jwt(payload, secret=SECRET):
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b'=')
    payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=')
    msg = b'.'.join([header, payload])
    sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest()).rstrip(b'=')
    return b'.'.join([header, payload, sig]).decode()

def decode_jwt(token, secret=SECRET):
    try:
        header_b64, payload_b64, sig_b64 = token.split('.')
        msg = f'{header_b64}.{payload_b64}'.encode()
        expected_sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest()).rstrip(b'=');
        if not hmac.compare_digest(expected_sig, sig_b64.encode()):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + '=='))
        if payload.get('exp') and payload['exp'] < int(time.time()):
            return None
        return payload
    except Exception:
        return None



def jwt_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return {"msg": "Missing or invalid token"}, status.UNAUTHORIZED
        token = auth.split(' ', 1)[1]
        payload = decode_jwt(token)
        if not payload:
            return make_response(jsonify({"msg": "Invalid or expired token"}), status.UNAUTHORIZED)
        g.user = payload['sub']
        return f(*args, **kwargs)
    return wrapper

