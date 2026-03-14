from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query
from fastapi import HTTPException 
import math
import psycopg2
import pandas as pd
import io
import tempfile
from dotenv import load_dotenv 
import os
import requests
import time

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # libera só seu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", 5432)
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

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
        
        response = requests.post(self.login_url, json=payload, timeout=10)
        # response.raise_for_status()
        
        # if response.status_code != 200:
        #   print("Erro API:", response.status_code, response.text)
        #   return None

        if response.status_code != 200:
          raise Exception("Falha ao validar token")

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
        response = requests.post(self.refresh_url, json=payload, timeout=10)

        # response.raise_for_status()
        # if response.status_code != 200:
        #   print("Erro API:", response.status_code, response.text)
        #   return None
        if response.status_code != 200:
          raise Exception("Falha ao validar token")

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
        return requests.request(method, url, headers=headers, timeout=10, **kwargs)
client = APIClient()

# def buscar_ean_por_familia(client, seq_familia):
#     url = f"https://irmaosmarafao171429.consinco.cloudtotvs.com.br:8343/CadastrosEstruturaisAPI/api/v1/Produto/produto-codigo?SeqFamilia={seq_familia}&TipoCodigo=E&QtdEmbalagem=1&PageSize=100"
#     response = client.request("GET", url)
#     if response.status_code != 200:
#       print("Erro API:", response.status_code, response.text)
#       return None
#     data = response.json()

#     # Se não retornou nada, exclui
#     if not data.get("items"):
#         return None

#     # Percorre os itens e procura o primeiro com indUtilVenda = "S"
#     for item in data["items"]:
#         if item.get("indUtilVenda") == "S":
#             return item.get("codigoAcesso")

#     # Se nenhum item válido encontrado, exclui
#     return None

def buscar_ean_por_produto(client, seq_produto):
    url = f"https://irmaosmarafao171429.consinco.cloudtotvs.com.br:8343/CadastrosEstruturaisAPI/api/v1/Produto/produto-codigo?SeqProduto={seq_produto}&TipoCodigo=E&QtdEmbalagem=1&PageSize=100"
    response = client.request("GET", url)
    if response.status_code != 200:
      print("Erro API:", response.status_code, response.text)
      return None
    data = response.json()

    # Se não retornou nada, exclui
    if not data.get("items"):
        return None

    # Percorre os itens e procura o primeiro com indUtilVenda = "S"
    for item in data["items"]:
        if item.get("indUtilVenda") == "S":
            print( seq_produto, item.get("codigoAcesso"))
            return item.get("codigoAcesso")

    # Se nenhum item válido encontrado, exclui
    return None

@app.post("/cotacoes/")
async def criar_cotacao(nome: str = Form(...), arquivo: UploadFile = File(...)):
    try:
        client.get_token()
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Falha de autenticação na API externa"
        )

    try:
        contents = await arquivo.read()
        df = pd.read_csv(io.BytesIO(contents), sep=";", encoding="latin1", header=None)

        # remover linhas completamente vazias
        df = df.dropna(how="all")

        # remover linhas que não possuem as 4 colunas necessárias
        df = df.dropna(subset=[0,1,2,3])

        # Se a primeira célula da primeira coluna for texto, removemos a linha (cabeçalho)
        if not df.empty and isinstance(df.iloc[0, 0], str):
            # Se for texto e não número, consideramos cabeçalho
            if not df.iloc[0, 0].isdigit():
                df = df.drop(index=0).reset_index(drop=True)

        # Renomear colunas para padronizar
        df.columns = ["CodigoProduto",  "ProdutoFamilia", "CodigoFamilia", "Embalagem"]

        # Limpeza básica
        df["CodigoFamilia"] = df["CodigoFamilia"].fillna("").astype(str).str.replace(".0", "", regex=False)
        df["CodigoProduto"] = df["CodigoProduto"].fillna("").astype(str).str.replace(".0", "", regex=False)
        df["ProdutoFamilia"] = df["ProdutoFamilia"].fillna("").astype(str)
        df["Embalagem"] = df["Embalagem"].fillna("").astype(str).str.strip()

        # Manter apenas linhas onde Embalagem é "UN 1"
        df = df[df["Embalagem"] == "UN 1"]

        # Remover duplicados por família
        df = df.drop_duplicates(subset=["CodigoFamilia"], keep="first")
              
         # Inserção no banco
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO cotacoes (nome, status) VALUES (%s, %s) RETURNING id", (nome, "A"))
        cotacao_id = cur.fetchone()[0]

        for _, row in df.iterrows():
          codigo_produto = row["CodigoProduto"]

          try:
              ean = buscar_ean_por_produto(client, codigo_produto)
              #print(codigo_produto, ean)
              
              if ean and len(ean) not in (13, 8):
                cur.execute("""
                        INSERT INTO itens_cotacao (cotacao_id, ean, familia, nome_produto, preco, promocional)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        cotacao_id,
                        ean,
                        codigo_familia,
                        produto_familia,
                        0,
                        "N"
                    ))
                
          except Exception as e:
              print("Erro no produto", codigo_produto, e)

        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Cotação e itens salvos no banco com sucesso!", "id": cotacao_id}
        # return {"linhas_processadas": len(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/versao")
def versao():
    return {"versao": "1.0.7", "mensagem": "API atualizadas"}