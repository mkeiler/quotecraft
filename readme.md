# QuoteCraft

Sistema completo de gerenciamento de orcamentos em Streamlit para pequenos negocios.

## Funcionalidades

- **Clientes**: Cadastro completo com nome, email, telefone, empresa e endereco
- **Servicos**: Catalogo de servicos com precos base e categorias
- **Orcamentos**: Criacao, edicao, controle de status (rascunho, enviado, aprovado, rejeitado)
- **PDF**: Geracao automatica de PDF profissional dos orcamentos
- **Email**: Envio de orcamentos por email via Gmail SMTP com PDF anexo
- **Link Publico**: Clientes visualizam orcamentos via link com token (sem login)
- **Autenticacao**: Acesso admin protegido por senha
- **Debug**: Painel de debug com logs, estatisticas e ferramentas

## Requisitos

- Python 3.10+
- Dependencias listadas em `requirements.txt`

## Instalacao Local

```bash
# Clonar o repositorio
git clone <url-do-repo>
cd quotecraft

# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar secrets (copiar e editar)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# Executar
streamlit run app.py
```

O banco de dados SQLite (`quotecraft.db`) e criado automaticamente na primeira execucao.

## Configuracao

### Arquivo `.streamlit/secrets.toml`

```toml
# Autenticacao do Admin
[auth]
username = "admin"
password_hash = "hash_sha256_da_senha"

# Configuracao SMTP (Gmail)
[smtp]
server = "smtp.gmail.com"
port = 587
email = "seuemail@gmail.com"
app_password = "xxxx xxxx xxxx xxxx"

# Configuracao do App
[app]
base_url = "https://seudominio.com"
token_expiry_days = 30
debug = false
```

### Gerar Hash de Senha

```python
import hashlib
hashlib.sha256("sua_senha_aqui".encode()).hexdigest()
```

Ou use o painel de Debug (`/Debug`) apos fazer login.

### Configurar Gmail SMTP

1. Acesse sua conta Google
2. Ative a **Verificacao em 2 etapas** em: https://myaccount.google.com/security
3. Gere uma **Senha de App** em: https://myaccount.google.com/apppasswords
4. Use a senha gerada (16 caracteres) no campo `app_password`

## Estrutura do Projeto

```
quotecraft/
├── .streamlit/
│   ├── config.toml              # Tema customizado
│   └── secrets.toml             # Credenciais (NAO COMMITAR!)
├── database/
│   ├── models.py                # Schema e migrations
│   └── operations.py            # Operacoes CRUD
├── pages/
│   ├── 1_👥_Clientes.py         # Gerenciamento de clientes
│   ├── 2_🛠️_Servicos.py         # Gerenciamento de servicos
│   ├── 3_📄_Orcamentos.py       # Gerenciamento de orcamentos
│   ├── 4_🔗_Visualizar_Orcamento.py  # Pagina publica (sem auth)
│   └── 5_🐛_Debug.py            # Painel de debug (admin)
├── services/
│   ├── auth.py                  # Autenticacao admin
│   ├── email_service.py         # Envio de emails SMTP
│   ├── pdf_generator.py         # Geracao de PDF
│   └── token_service.py         # Tokens para links publicos
├── utils/
│   ├── debug.py                 # Logging e utilidades de debug
│   ├── helpers.py               # Funcoes auxiliares
│   └── validators.py            # Validacoes de entrada
├── logs/                        # Logs do sistema (auto-criado)
├── output/                      # PDFs gerados (auto-criado)
├── app.py                       # Homepage
├── requirements.txt
└── README.md
```

## Deploy em Producao

### Opcao 1: Streamlit Community Cloud (Gratuito)

1. Suba o codigo para um repositorio GitHub
2. Acesse https://share.streamlit.io
3. Conecte seu repositorio
4. Configure os secrets no painel do Streamlit Cloud:
   - Va em "Settings" > "Secrets"
   - Cole o conteudo de `secrets.toml`
5. Deploy automatico!

**Importante**: O Streamlit Cloud usa sistema de arquivos efemero. Para persistencia de dados, considere usar um banco externo (PostgreSQL, etc).

### Opcao 2: VPS / Servidor Linux

```bash
# Instalar dependencias do sistema
sudo apt update
sudo apt install python3.10 python3.10-venv nginx

# Criar usuario para o app
sudo useradd -m -s /bin/bash quotecraft
sudo su - quotecraft

# Clonar e configurar
git clone <url-do-repo> ~/quotecraft
cd ~/quotecraft
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
nano .streamlit/secrets.toml  # Editar com suas credenciais
```

Criar servico systemd `/etc/systemd/system/quotecraft.service`:

```ini
[Unit]
Description=QuoteCraft Streamlit App
After=network.target

[Service]
User=quotecraft
WorkingDirectory=/home/quotecraft/quotecraft
Environment="PATH=/home/quotecraft/quotecraft/venv/bin"
ExecStart=/home/quotecraft/quotecraft/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Ativar e iniciar servico
sudo systemctl daemon-reload
sudo systemctl enable quotecraft
sudo systemctl start quotecraft
```

Configurar Nginx como proxy reverso `/etc/nginx/sites-available/quotecraft`:

```nginx
server {
    listen 80;
    server_name seudominio.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/quotecraft /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Configurar HTTPS com Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seudominio.com
```

### Opcao 3: Docker

Criar `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
# Build e run
docker build -t quotecraft .
docker run -d -p 8501:8501 -v $(pwd)/.streamlit:/app/.streamlit quotecraft
```

## Checklist de Producao

- [ ] Alterar senha do admin (gerar novo hash)
- [ ] Configurar `base_url` com URL de producao
- [ ] Configurar credenciais Gmail (App Password)
- [ ] Desativar modo debug: `debug = false`
- [ ] Configurar HTTPS (SSL/TLS)
- [ ] Configurar backup do banco de dados
- [ ] Adicionar `.streamlit/secrets.toml` ao `.gitignore`

## Seguranca

- Senhas armazenadas como hash SHA-256
- Tokens de acesso gerados com `secrets.token_urlsafe(32)` (256 bits)
- Credenciais SMTP em arquivo separado (secrets.toml)
- Queries SQL parametrizadas (prevencao de SQL injection)
- Pagina publica nao expoe dados administrativos

## Logs e Debug

Com `debug = true` em secrets.toml:

- Logs salvos em `logs/quotecraft.log`
- Painel de debug em `/Debug` (requer login admin)
- Funcionalidades do painel:
  - Visualizar session state
  - Explorar banco de dados
  - Filtrar e limpar logs
  - Testar configuracao de email
  - Validar tokens
  - Gerar hashes de senha

## Licenca

Projeto privado desenvolvido para uso interno.
