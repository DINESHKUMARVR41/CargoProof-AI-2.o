from fastapi import Header, HTTPException
from .config import settings
import jwt, httpx

def current_user(authorization: str|None=Header(default=None)):
    if not authorization or not authorization.lower().startswith('bearer '):
        if settings.demo_mode and not settings.supabase_url:return {'id':'demo-user','email':'demo@cargoproof.local','role':'user'}
        raise HTTPException(401,'Missing Supabase access token')
    token=authorization.split(' ',1)[1]
    if settings.supabase_url and settings.supabase_anon_key:
        try:
            r=httpx.get(settings.supabase_url.rstrip('/')+'/auth/v1/user',headers={'apikey':settings.supabase_anon_key,'Authorization':f'Bearer {token}'},timeout=8)
            if r.status_code!=200:raise ValueError('Supabase rejected access token')
            claims=r.json(); return {'id':claims['id'],'email':claims.get('email'),'role':claims.get('app_metadata',{}).get('role','user')}
        except Exception as exc:raise HTTPException(401,'Invalid or expired Supabase access token') from exc
    if not settings.supabase_jwt_secret:raise HTTPException(503,'Configure Supabase URL + anon key to validate sessions')
    try:
        claims=jwt.decode(token,settings.supabase_jwt_secret,algorithms=['HS256'],audience=settings.supabase_jwt_audience)
        return {'id':claims['sub'],'email':claims.get('email'),'role':claims.get('app_metadata',{}).get('role','user')}
    except Exception as exc:raise HTTPException(401,'Invalid or expired access token') from exc
