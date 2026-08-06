# ativar ambiente virtual

python3 -m venv venv
source venv/bin/activate

# se de erro
.\venv\Scripts\Activate.ps1


python -m pip install --upgrade pip

pip install fastapi "uvicorn[standard]" anthropic python-dotenv httpx oracledb


# instalar o dastapi
pip install fastapi uvicorn

pip install anthropic python-dotenv httpx
pip install anthropic httpx python-dotenv

# iniciar projeto
npx omniroute@latest

uvicorn main:app --reload