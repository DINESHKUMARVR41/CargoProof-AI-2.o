from fastapi import Header, HTTPException
from .config import settings
import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials


def _firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        # Uses GOOGLE_APPLICATION_CREDENTIALS pointing to a Firebase service-account JSON file.
        options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
        return firebase_admin.initialize_app(credentials.ApplicationDefault(), options=options)


def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith('bearer '):
        if settings.demo_mode:
            return {'id': 'demo-user', 'email': 'demo@cargoproof.local', 'role': 'user'}
        raise HTTPException(401, 'Missing Firebase ID token')
    token = authorization.split(' ', 1)[1]
    if not settings.firebase_project_id:
        raise HTTPException(503, 'Configure FIREBASE_PROJECT_ID and Firebase Admin credentials')
    try:
        claims = firebase_auth.verify_id_token(token, app=_firebase_app(), check_revoked=True)
        return {'id': claims['uid'], 'email': claims.get('email'), 'role': claims.get('role', 'admin' if claims.get('admin') else 'user')}
    except Exception as exc:
        raise HTTPException(401, 'Invalid or expired Firebase ID token') from exc
