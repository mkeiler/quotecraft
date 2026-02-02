# QuoteCraft

Sistema de gerenciamento de orçamentos em Streamlit para pequeno negócio.

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

O banco de dados SQLite (`quotecraft.db`) é criado automaticamente na primeira execução.

## Estrutura do Projeto

```
quotecraft/
├── .streamlit/
│   └── config.toml          # Tema customizado
├── database/
│   ├── __init__.py
│   ├── models.py            # Schema e inicialização do banco
│   └── operations.py        # Operações CRUD
├── pages/
│   ├── 1_👥_Clientes.py     # Gerenciamento de clientes
│   └── 2_🛠️_Servicos.py     # Gerenciamento de serviços
├── utils/
│   ├── __init__.py
│   └── validators.py        # Validações de entrada
├── .env.example
├── .gitignore
├── app.py                   # Homepage
├── requirements.txt
└── README.md
```

## Funcionalidades (Fase 1)

- **Clientes**: Cadastro, edição, exclusão e busca por nome/e-mail
- **Serviços**: Cadastro, edição, ativação/desativação e filtro por categoria
- **Dashboard**: Métricas resumidas na homepage

## Roadmap

- **Fase 2**: Orçamentos (criação, itens, cálculo de totais)
- **Fase 3**: Geração de PDF e envio por e-mail
- **Fase 4**: Autenticação e controle de acesso
