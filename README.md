# Assistente RESPAD/CBMAL

Assistente de planejamento operacional para resposta a desastres do CBMAL, baseado na doutrina RESPAD/DNAISP.

## Setup local
pip install -r requirements.txt
uvicorn main:app --reload

## Deploy (Render.com)
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Variável de ambiente: `GEMINI_API_KEY`
