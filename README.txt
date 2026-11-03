Dashboard Quadro de Medalhas Olímpicas (1992-2020) - Dash + Plotly Express

Dupla:
  - Francisco Carlos de Assis Santos Junior
  - Luan Souza Cunha

Link do dashboard no Render: https://dashboard-medalhas-vd.onrender.com

Executar localmente:
  pip install -r requirements.txt
  python app.py        (http://127.0.0.1:8050)

Deploy no Render (Web Service):
  Build Command: pip install -r requirements.txt
  Start Command: gunicorn app:server

Arquivos: app.py, assets/style.css, requirements.txt, Country_Medals.csv
