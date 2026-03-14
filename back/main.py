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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cotacoes")
def listar_cotacoes():
    """Lista todas as cotações"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nome, status, data_criacao FROM cotacoes ORDER BY id DESC")
        cotacoes = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": c[0], "nome": c[1], "status": c[2], "data_criacao": c[3]} for c in cotacoes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cotacao/{cotacao_id}")
def info_cotacao(cotacao_id: int):
    """Lista dados da cotação"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nome, status, data_criacao FROM cotacoes WHERE id = %s",(cotacao_id,))
        cotacao = cur.fetchone()
        cur.close()
        conn.close()
        return {"id": cotacao[0], "nome": cotacao[1], "status": cotacao[2], "data_criacao": cotacao[3]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cotacoes/finalizadas")
def listar_cotacoes_finalizadas():
    """Mostra as cotações finalizadas para gerar o arquivo de importação"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nome, status, data_criacao FROM cotacoes WHERE status = %s ORDER BY id DESC", ("F",))
        cotacoes = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": c[0], "nome": c[1], "status": c[2], "data_criacao": c[3]} for c in cotacoes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cotacoes/{cotacao_id}/itens")
def listar_itens_cotacao(
    cotacao_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """Lista itens da cotação com paginação"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""SELECT id, ean, familia, nome_produto, preco, promocional FROM itens_cotacao WHERE cotacao_id = %s ORDER BY id OFFSET %s LIMIT %s""", (cotacao_id, offset, limit))
        itens = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {"id": i[0], "ean": i[1], "familia": i[2],
             "nome_produto": i[3], "preco": i[4], "promocional": i[5]}
            for i in itens
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cotacoes/{cotacao_id}/itens/total")
def contar_itens_cotacao(cotacao_id: int):
    """Retorna o total de itens da cotação"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM itens_cotacao WHERE cotacao_id = %s", (cotacao_id,))
        total = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {"total_itens": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import HTTPException
import math

@app.put("/cotacoes/{cotacao_id}/itens/preco")
def atualizar_preco_item(cotacao_id: int, familia: int, preco: float, promocional: str = "N"):
    """Atualiza preço da cotação """
    try:
        # Validação do preço
        if math.isnan(preco) or math.isinf(preco) or preco < 0:
            raise HTTPException(status_code=400, detail="Preço inválido")

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE itens_cotacao SET preco = %s, promocional = %s WHERE cotacao_id = %s AND familia = %s",
            (preco, promocional, cotacao_id, familia)
        )
        conn.commit()
        cur.close()
        conn.close()

        return {
            "message": f"Preço do item {familia} atualizado com sucesso",
            "cotacao": cotacao_id,
            "preco": f"{preco:.2f}",
            "promocional": promocional
        }
    except HTTPException:
        # Repassa o erro de validação
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cotacoes/{cotacao_id}/familia/{familia_id}")
def detalhes_cotacao(cotacao_id: int, familia_id: str):
    """recupera um item da cotacao"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, ean, familia, nome_produto, preco, promocional FROM itens_cotacao WHERE cotacao_id = %s AND familia = %s", (cotacao_id,familia_id))
        itens = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": i[0], "ean": i[1], "familia": i[2], "nome_produto": i[3], "preco": i[4], "promocional": i[5]} for i in itens]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/cotacoes/{cotacao_id}/finalizar")
def finalizar_cotacao(cotacao_id: int):
    """Finaliza uma cotação"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE cotacoes SET status = %s WHERE id = %s", ("F", cotacao_id))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": f"Cotação {cotacao_id} finalizada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/cotacoes/{cotacao_id}")
def excluir_cotacao(cotacao_id: int):
    """Exclui uma cotação"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM cotacoes WHERE id = %s", (cotacao_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": f"Cotação {cotacao_id} excluída com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cotacoes/{cotacao_id}/gerar-arquivo")
def gerar_arquivo_cotacao(cotacao_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT ean, preco
            FROM itens_cotacao
            WHERE cotacao_id = %s AND preco > 0
            ORDER BY id
        """, (cotacao_id,))
        itens = cur.fetchall()
        cur.close()
        conn.close()

        linhas = []
        for ean, preco in itens:
            ean_str = str(ean).zfill(13)
            preco_centavos = int(round(preco * 100))
            preco_str = str(preco_centavos).zfill(7)
            linha = "0000000" + ean_str + preco_str
            linhas.append(linha)

        # cria arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmpfile:
            tmpfile.write("\n".join(linhas))
            caminho = tmpfile.name

        return FileResponse(caminho, media_type="text/plain", filename=f"cotacao_{cotacao_id}.txt")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/versao")
def versao():
    return {"versao": "1.0.7", "mensagem": "API atualizadas"}