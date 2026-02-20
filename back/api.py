import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

class APIClient:
    def __init__(self):
        # Credenciais vindas de variáveis de ambiente
        self.company = os.getenv("API_COMPANY")
        self.username = os.getenv("API_USERNAME")
        self.password = os.getenv("API_PASSWORD")

        # Endpoints
        self.login_url = "https://irmaosmarafao171429.consinco.cloudtotvs.com.br:8343/api/v1/auth/login"
        self.refresh_url = "https://irmaosmarafao171429.consinco.cloudtotvs.com.br:8343/api/v1/auth/refresh-token"

        # Tokens
        self.access_token = None
        self.refresh_token = None
        self.token_type = None
        self.expires_at = None  # timestamp de expiração

    def login(self):
        
        payload = {
            "company": self.company,
            "username": self.username,
            "password": self.password
        }
        
        response = requests.post(self.login_url, json=payload)
        response.raise_for_status()
        data = response.json()

        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.token_type = data["token_type"]
        # Guardar o momento em que expira
        self.expires_at = time.time() + data["expires_in"]

    def refresh(self):
        payload = {
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        response = requests.post(self.refresh_url, json=payload)
        response.raise_for_status()
        data = response.json()

        self.access_token = data["access_token"]
        # Algumas APIs devolvem um novo refresh_token, outras não
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        self.token_type = data["token_type"]
        self.expires_at = time.time() + data["expires_in"]

    def get_token(self):
        # Se não tem token ou já expirou, renova
        if not self.access_token:
            self.login()
        elif time.time() >= self.expires_at:
            self.refresh()
        return f"{self.token_type} {self.access_token}"

    def request(self, method, url, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = self.get_token()
        return requests.request(method, url, headers=headers, **kwargs)


# Exemplo de uso
if __name__ == "__main__":
    client = APIClient()

    # Chamar qualquer endpoint protegido
    response = client.request("GET", "https://irmaosmarafao171429.consinco.cloudtotvs.com.br:8343/CadastrosEstruturaisAPI/api/v1/Produto/produto-codigo?SeqFamilia=48199&TipoCodigo=E&QtdEmbalagem=1&PageSize=100")
    data=response.json()
    print(data["items"][0]["codigoAcesso"])
