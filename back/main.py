from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query
from fastapi import HTTPException 
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
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

_token_cache = {
    "access_token": None,
    "refresh_token": None,
    "expires_at": 0,
    "token_type": "Bearer"
}
_token_lock = Lock()

class APIClient:
    def __init__(self):
        # Credenciais vindas de variáveis de ambiente
        self.company = os.getenv("API_COMPANY")
        self.username = os.getenv("API_USERNAME")
        self.password = os.getenv("API_PASSWORD")

        # Endpoints
        self.login_url = "https://irmaosmarafao171429.consinco.cloudtotvs.com.br:8343/api/v1/auth/login"
        self.refresh_url = "https://irmaosmarafao171429.consinco.cloudtotvs.com.br:8343/api/v1/auth/refresh-token"

    def login(self):
        global _token_cache

        payload = {
            "company": self.company,
            "username": self.username,
            "password": self.password
        }
        
        response = requests.post(self.login_url, json=payload, timeout=10)

        if response.status_code != 200:
          raise Exception("Falha ao validar token")

        data = response.json()

        _token_cache["access_token"] = data["access_token"]
        _token_cache["refresh_token"] = data["refresh_token"]
        _token_cache["expires_at"] = time.time() + data["expires_in"]
        _token_cache["token_type"] = data["token_type"]

    def refresh(self):
        global _token_cache

        payload = {
            "refresh_token": _token_cache["refresh_token"],
            "grant_type": "refresh_token"
        }
        response = requests.post(self.refresh_url, json=payload, timeout=10)

        if response.status_code != 200:
            # se falhar refresh → faz login novo
            self.login()
            return

        data = response.json()

        _token_cache["access_token"] = data["access_token"]
        _token_cache["refresh_token"] = data.get("refresh_token", _token_cache["refresh_token"])
        _token_cache["expires_at"] = time.time() + data["expires_in"]
        _token_cache["token_type"] = data["token_type"]

    def get_token(self):
        # Se não tem token ou já expirou, renova
        global _token_cache

        with _token_lock:
            if not _token_cache["access_token"]:
                self.login()
            elif time.time() >= _token_cache["expires_at"]:
                self.refresh()

            return f'{_token_cache["token_type"]} {_token_cache["access_token"]}'

    def request(self, method, url, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = self.get_token()
        return requests.request(method, url, headers=headers, timeout=10, **kwargs)
# client = APIClient()

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
            # print( seq_produto, item.get("codigoAcesso"))
            return item.get("codigoAcesso")

    # Se nenhum item válido encontrado, exclui
    return None

def processar_produto(row, client):
    codigo_produto = row["CodigoProduto"]
    codigo_familia = row["CodigoFamilia"]
    produto_familia = row["ProdutoFamilia"]

    try:
        ean = buscar_ean_por_produto(client, codigo_produto)

        if ean and len(str(ean)) in (13, 8):
            return (codigo_produto, codigo_familia, produto_familia, ean)

    except Exception as e:
        print("Erro no produto", codigo_produto, e)

    return None

@app.post("/cotacoes")
async def criar_cotacao(nome: str = Form(...), arquivo: UploadFile = File(...)):
    client = APIClient()
    try:
        client.get_token()
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Falha de autenticação na API externa"
        )

    try:
        contents = await arquivo.read()

        # =========================
        # Decodificar arquivo
        # =========================
        encodings = ["utf-8", "utf-8-sig", "latin1"]
        for enc in encodings:
            try:
                texto = contents.decode(enc)
                break
            except Exception:
                continue
        else:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível ler o arquivo. Encoding inválido."
            )

        # =========================
        # Filtrar linhas válidas (4 colunas)
        # =========================
        linhas = texto.splitlines()

        linhas_validas = []
        for linha in linhas:
            if linha.count(";") == 3:  # 4 colunas
                linhas_validas.append(linha)

        if not linhas_validas:
            raise HTTPException(
                status_code=400,
                detail="Arquivo não possui linhas válidas."
            )

        # =========================
        # Separar header e dados
        # =========================
        header = linhas_validas[0]
        dados = linhas_validas[1:]

        colunas_esperadas = [
            "Código Produto",
            "Produto : Família",
            "Código Família",
            "Embalagem Unitária"
        ]

        colunas_recebidas = [c.strip() for c in header.split(";")]

        if colunas_recebidas != colunas_esperadas:
            raise HTTPException(
                status_code=400,
                detail="Cabeçalho inválido."
            )

        # =========================
        # Criar DataFrame limpo
        # =========================

        csv_limpo = "\n".join(dados)

        df = pd.read_csv(
            io.StringIO(csv_limpo),
            sep=";",
            header=None
        )

        df.columns = [
            "CodigoProduto",
            "ProdutoFamilia",
            "CodigoFamilia",
            "Embalagem"
        ]

        # =========================
        # Limpeza
        # =========================
        df["CodigoProduto"] = (
            df["CodigoProduto"]
            .fillna("")
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        df["CodigoFamilia"] = (
            df["CodigoFamilia"]
            .fillna("")
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        df["ProdutoFamilia"] = df["ProdutoFamilia"].fillna("").astype(str)

        df["Embalagem"] = (
            df["Embalagem"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # =========================
        # Filtros
        # =========================
        df = df[
            df["CodigoProduto"].str.fullmatch(r"\d+") &
            df["CodigoFamilia"].str.fullmatch(r"\d+")
        ]

        df = df[df["Embalagem"] == "UN 1"]

        df = df.drop_duplicates(subset=["CodigoFamilia"], keep="first")

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="Nenhum item válido encontrado no CSV."
            )

        # =========================
        # Banco
        # =========================
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO cotacoes (nome, status) VALUES (%s, %s) RETURNING id",
            (nome, "A")
        )
        cotacao_id = cur.fetchone()[0]

        # ======================
        # PROCESSAMENTO PARALELO
        # ======================
        resultados = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(processar_produto, row, client)
                for _, row in df.iterrows()
            ]

            for future in as_completed(futures):
                result = future.result()
                if result:
                    resultados.append(result)


        # ======================
        # INSERÇÃO NO BANCO
        # ======================
        for codigo_produto, codigo_familia, produto_familia, ean in resultados:
            try:
                cur.execute("""
                    INSERT INTO itens_cotacao 
                    (cotacao_id, ean, familia, nome_produto, preco, promocional)
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
                print("Erro ao inserir no banco:", codigo_produto, e)


        conn.commit()
        cur.close()
        conn.close()

        return {
            "message": "Cotação e itens salvos com sucesso!",
            "id": cotacao_id,
            "linhas_validas": len(df),
            "linhas_descartadas": len(linhas) - len(linhas_validas)
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Erro interno no servidor"
        )

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
    return {"versao": "1.0.12", "mensagem": "API atualizadas"}