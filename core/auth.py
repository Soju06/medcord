from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import env

auth_scheme = HTTPBearer()


def upload_role(token: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    if env.PASSWORD and token.credentials != env.PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )
