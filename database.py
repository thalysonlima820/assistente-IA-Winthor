from pathlib import Path
import os

import oracledb
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

oracledb.init_oracle_client(
    lib_dir=str(BASE_DIR / "DB" / "instantclient_23_3")
)

def conectar():
    conexao = oracledb.connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=os.getenv("ORACLE_DSN"),
    )

    return conexao