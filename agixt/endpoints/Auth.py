from fastapi import APIRouter, Request, Header, Depends, HTTPException
from Models import Detail, Login, UserInfo, Register
from MagicalAuth import MagicalAuth, verify_api_key
from Agent import webhook_create_user
from ApiClient import get_api_client, is_admin
from Models import WebhookUser
from Globals import getenv
import pyotp

app = APIRouter()


@app.post("/v1/user")
def register(register: Register):
    mfa_token = MagicalAuth().register(new_user=register)
    totp = pyotp.TOTP(mfa_token)
    otp_uri = totp.provisioning_uri(name=register.email, issuer_name=getenv("APP_NAME"))
    return {"otp_uri": otp_uri}


@app.get("/v1/user/exists", response_model=bool, summary="Check if user exists")
def get_user(email: str) -> bool:
    try:
        return MagicalAuth().user_exists(email=email)
    except:
        return False


@app.get(
    "/v1/user",
    dependencies=[Depends(verify_api_key)],
    summary="Get user details",
)
def log_in(
    request: Request,
    authorization: str = Header(None),
):
    auth = MagicalAuth(token=authorization)
    user_data = auth.login(ip_address=request.client.host)
    user_preferences = auth.get_user_preferences()
    return {
        "email": user_data.email,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        **user_preferences,
    }


@app.post(
    "/v1/login",
    response_model=Detail,
    summary="Login with email and OTP token",
)
async def send_magic_link(request: Request, login: Login):
    auth = MagicalAuth()
    data = await request.json()
    referrer = None
    if "referrer" in data:
        referrer = data["referrer"]
    magic_link = auth.send_magic_link(
        ip_address=request.client.host, login=login, referrer=referrer
    )
    return Detail(detail=magic_link)


@app.put(
    "/v1/user",
    dependencies=[Depends(verify_api_key)],
    response_model=Detail,
    summary="Update user details",
)
def update_user(update: UserInfo, request: Request, authorization: str = Header(None)):
    response = request.json()
    user = MagicalAuth(token=authorization).update_user(
        ip_address=request.client.host,
        **update.model_dump(),
        **response,
    )
    return Detail(detail=user)


# Delete user
@app.delete(
    "/v1/user",
    dependencies=[Depends(verify_api_key)],
    response_model=Detail,
    summary="Delete user",
)
def delete_user(
    user=Depends(verify_api_key),
    authorization: str = Header(None),
):
    MagicalAuth(token=authorization).delete_user()
    return Detail(detail="User deleted successfully.")


# Webhook user creations from other applications
@app.post("/api/user", tags=["User"])
async def createuser(
    account: WebhookUser,
    authorization: str = Header(None),
):
    ApiClient = get_api_client(authorization=authorization)
    return webhook_create_user(
        api_key=authorization,
        email=account.email,
        role="user",
        agent_name=account.agent_name,
        settings=account.settings,
        commands=account.commands,
        training_urls=account.training_urls,
        github_repos=account.github_repos,
        zip_file_content=account.zip_file_content,
        ApiClient=ApiClient,
    )


@app.post(
    "/v1/oauth2/{provider}",
    response_model=Detail,
    summary="Login using OAuth2 provider",
)
async def oauth_login(request: Request, provider: str):
    data = await request.json()
    auth = MagicalAuth()
    magic_link = auth.sso(
        provider=provider.lower(),
        code=data["code"],
        ip_address=request.client.host,
        referrer=data["referrer"] if "referrer" in data else getenv("MAGIC_LINK_URL"),
    )
    return {"detail": magic_link, "email": auth.email, "token": auth.token}
