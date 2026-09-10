"""
Script de inicialização (seed script).

Objetivo: criar a tabela "usuarios" (caso ainda não exista) e cadastrar
o primeiro usuário com papel de Administrador Master.

Quando usar:
- Na primeira execução do sistema, antes de haver qualquer usuário cadastrado.
- Em caso de emergência, se o admin perder o acesso (recriando um novo
  usuário administrador manualmente).

Este script é idempotente em relação à tabela (usa CREATE TABLE IF NOT EXISTS),
mas NÃO deve ser executado repetidamente com os mesmos dados de login,
pois a coluna "login" é única (UNIQUE) e a segunda execução falhará
de forma controlada (ver tratamento de exceção abaixo).
"""

import sqlite3
from werkzeug.security import generate_password_hash

conexao = sqlite3.connect("monitoramento_condominios.db")
cursor = conexao.cursor()

# 1. Garante que a tabela de usuários existe no banco
cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        login TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL,
        cargo TEXT NOT NULL DEFAULT 'comum',
        precisa_trocar_senha INTEGER DEFAULT 1,
        ativo INTEGER DEFAULT 1
    )
""")

# 2. Dados do Admin Master — AJUSTE ANTES DE EXECUTAR
nome_completo = "admin exemplo"          # nome completo do administrador
senha_numerica = "000000"                # PIN numérico de 6 dígitos (deve ser trocado no primeiro login)

# Gera o login automaticamente no padrão "nome.sobrenome" (tudo em minúsculas)
partes = nome_completo.strip().lower().split()
login = f"{partes[0]}.{partes[-1]}" if len(partes) > 1 else partes[0]

# 3. Gera o hash da senha — nunca armazenamos senha em texto puro no banco
senha_hash = generate_password_hash(senha_numerica)

# 4. Insere o Admin Master no banco.
#    precisa_trocar_senha = 0 porque o admin master já entra com senha
#    definitiva; usuários comuns (ver salvar_usuario em app_v1.py) são
#    criados com precisa_trocar_senha = 1.
#    O bloco try/except trata o caso de o login já existir, já que a
#    coluna "login" é UNIQUE — evita que a segunda execução do script
#    derrube o programa com um erro não tratado.
try:
    cursor.execute("""
        INSERT INTO usuarios (nome, login, senha_hash, cargo, precisa_trocar_senha, ativo)
        VALUES (?, ?, ?, 'admin', 0, 1)
    """, (nome_completo, login, senha_hash))
    conexao.commit()
    print(f"✔ Admin Master criado com sucesso! Login: {login}")
except sqlite3.IntegrityError:
    print(f"⚠ Já existe um usuário com o login '{login}'. Nada foi alterado.")

# 5. Encerra a conexão com o banco
conexao.close()
