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
import oracledb

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

def get_oracle_connection(): 
    return oracledb.connect( 
        user=os.getenv("ORA_USER"), 
        password=os.getenv("ORA_PASSWORD"), 
        dsn=os.getenv("ORA_DSN") # exemplo: "host:porta/servico" 
    )

# ---------------- ENDPOINTS ----------------

@app.post("/cotacoes")
async def criar_cotacoes(nome: str = Form(...), arquivo: UploadFile = File(...)):
    try:
        contents = await arquivo.read()
        df = pd.read_csv(io.BytesIO(contents), sep=";", header=None, encoding="latin1")

        familias = df[0].astype(str).tolist()
        if familias and not familias[0].isdigit():
            familias = familias[1:]

        familias = [f.strip() for f in familias if f.strip()]
        familias = list(set(familias))

        # Conexão Oracle 
        conn_ora = get_oracle_connection() 
        cur_ora = conn_ora.cursor()

        resultado = []

        for familia in familias:
            cur_ora.execute("""
                SELECT p.codacesso AS EAN,
                       p.seqfamilia,
                       d.desccompleta || ' : ' || f.familia AS nome
                FROM consinco.map_prodcodigo p
                INNER JOIN consinco.mrl_prodempseg s
                  ON p.seqproduto = s.seqproduto
                 AND p.qtdembalagem = s.qtdembalagem
                INNER JOIN consinco.map_produto d
                  ON p.seqproduto = d.seqproduto
                 AND p.seqfamilia = d.seqfamilia
                INNER JOIN consinco.map_familia f
                  ON p.seqfamilia = f.seqfamilia
                WHERE p.seqfamilia = :fam
                  AND p.tipcodigo = 'E'
                  AND p.indutilvenda = 'S'
                  AND p.qtdembalagem = 1
                  AND s.nroempresa = 1
                  AND s.nrosegmento = 1
                  AND s.statusvenda = 'A'
                  AND ROWNUM = 1
            """, {"fam": familia})
            row = cur_ora.fetchone()
            if row and row[0]:
                resultado.append({
                    "ean": row[0],
                    "familia": row[1],
                    "nome": row[2]
                })

        cur_ora.close() 
        conn_ora.close()

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO cotacoes (nome, status) VALUES (%s, %s) RETURNING id", (nome, "A"))
        cotacao_id = cur.fetchone()[0]

        for item in resultado:
            cur.execute("""
                INSERT INTO itens_cotacao (cotacao_id, ean, familia, nome_produto, preco, promocional)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                cotacao_id,
                item["ean"],
                item["familia"],
                item["nome"],
                0,
                'N'
            ))

        conn.commit()
        cur.close()
        conn.close()

        return {
            "cotacao": cotacao_id,
            "message": "Lista de famílias processada com sucesso",
            "dados": resultado,
            "total": len(resultado)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


