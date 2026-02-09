from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query
import psycopg2
import pandas as pd
import io
import tempfile
from dotenv import load_dotenv 
import os 

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # libera só seu frontend
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

# ---------------- ENDPOINTS ----------------

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
        return [{"id": cotacao[0], "nome": cotacao[1], "status": cotacao[2], "data_criacao": cotacao[3]}]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cotacoes")
async def criar_cotacao(nome: str = Form(...), arquivo: UploadFile = File(...)):
    try:
        contents = await arquivo.read()
        df = pd.read_csv(io.BytesIO(contents), sep=";", encoding="latin1")

        # Garantir colunas
        required_cols = ['Código EAN/Interno *', 'Código Família', 'Produto : Família']
        for col in required_cols:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Coluna {col} não encontrada no CSV")

        # Limpeza
        df['Código EAN/Interno *'] = df['Código EAN/Interno *'].fillna("").astype(str).str.replace('.0','', regex=False)
        df['Código Família'] = df['Código Família'].fillna("").astype(str).str.replace('.0','', regex=False)

        # Ajuste do filtro (>=3 dígitos, por exemplo)
        df = df[df['Código EAN/Interno *'].str.len() >= 7]
        df = df.drop_duplicates(subset=['Código Família'], keep='first')

        # Inserção no banco
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO cotacoes (nome, status) VALUES (%s, %s) RETURNING id", (nome, "A"))
        cotacao_id = cur.fetchone()[0]

        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO itens_cotacao (cotacao_id, ean, familia, nome_produto, preco, promocional)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                cotacao_id,
                row['Código EAN/Interno *'],
                row['Código Família'],
                row['Produto : Família'],
                0,
                'N'
            ))

        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Cotação e itens salvos no banco com sucesso!", "id": cotacao_id}

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
        cur.execute("""
            SELECT id, ean, familia, nome_produto, preco, promocional
            FROM itens_cotacao
            WHERE cotacao_id = %s
            ORDER BY id
            OFFSET %s LIMIT %s
        """, (cotacao_id, offset, limit))
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

@app.put("/cotacoes/{cotacao_id}/itens/preco")
def atualizar_preco_item(cotacao_id: int, familia: int, preco:float, promocional: str = "N"):
    """Atualiza preço da cotação """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute( "UPDATE itens_cotacao SET preco = %s, promocional = %s WHERE cotacao_id = %s AND familia = %s", (preco, promocional, cotacao_id, familia) )
        conn.commit()
        cur.close()
        conn.close()

        return { 
            "message": f"Preço do item {familia} atualizado com sucesso", 
            "cotacao": cotacao_id,
            "preco": f"{preco:.2f}", 
            "promocional": promocional 
        }
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
    return {"versao": "1.0.1", "mensagem": "API atualizadas"}
 