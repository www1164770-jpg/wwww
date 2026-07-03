
import os
import secrets
from urllib.parse import urlencode

import requests


class AuthingService:
    def __init__(self):
        self.issuer = os.getenv("AUTHING_ISSUER", "").rstrip("/")
        self.client_id = os.getenv("AUTHING_APP_ID")
        self.client_secret = os.getenv("AUTHING_APP_SECRET")
        self.redirect_uri = os.getenv("AUTHING_REDIRECT_URI")

        if not self.issuer:
            raise RuntimeError("AUTHING_ISSUER is not configured")
        if not self.client_id:
            raise RuntimeError("AUTHING_APP_ID is not configured")
        if not self.client_secret:
            raise RuntimeError("AUTHING_APP_SECRET is not configured")
        if not self.redirect_uri:
            raise RuntimeError("AUTHING_REDIRECT_URI is not configured")

        self._openid_config = None

    def get_openid_config(self):
        if self._openid_config:
            return self._openid_config

        url = f"{self.issuer}/.well-known/openid-configuration"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        self._openid_config = response.json()
        return self._openid_config

    def build_login_url(self, state):
        config = self.get_openid_config()
        authorization_endpoint = config["authorization_endpoint"]

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid profile email phone",
            "state": state,
            "nonce": secrets.token_urlsafe(16),
        }

        return f"{authorization_endpoint}?{urlencode(params)}"

    def exchange_code_for_token(self, code):
        config = self.get_openid_config()
        token_endpoint = config["token_endpoint"]

        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = requests.post(
            token_endpoint,
            data=data,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()

        return response.json()

    def get_user_info(self, access_token):
        config = self.get_openid_config()
        userinfo_endpoint = config["userinfo_endpoint"]

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        response = requests.get(
            userinfo_endpoint,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()

        return response.json()