from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import sqlite3
import pandas
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

# Chave usada pelo Flask para assinar o cookie de sessão.
# Troque por um valor aleatório antes de colocar em produção.
app.secret_key = os.environ.get("SECRET_KEY", "chave-de-desenvolvimento")


# -----------------------------------------------------------------------
# DECORATOR: protege rotas que exigem usuário logado
# -----------------------------------------------------------------------
def login_required(funcao):
    @wraps(funcao)
    def rota_protegida(*args, **kwargs):
        if "id_usuario" not in session:
            return redirect(url_for("login"))
        return funcao(*args, **kwargs)
    return rota_protegida


def admin_required(funcao):
    @wraps(funcao)
    def rota_protegida(*args, **kwargs):
        if session.get("cargo") != "admin":
            return "Acesso restrito ao Administrador Master.", 403
        return funcao(*args, **kwargs)
    return rota_protegida


# -----------------------------------------------------------------------
# LOGIN
# -----------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_digitado = request.form.get("login", "").strip().lower()
        senha_digitada = request.form.get("senha", "").strip()

        conexao = sqlite3.connect("monitoramento_condominios.db")
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT id_usuario, nome, senha_hash, cargo, ativo
            FROM usuarios
            WHERE login = ?
        """, (login_digitado,))
        usuario = cursor.fetchone()
        conexao.close()

        # Caso 1: usuário não existe (ou está desativado) -> mensagem específica
        if not usuario or usuario[4] == 0:
            return render_template("login.html",
                                    erro="Usuário não cadastrado.",
                                    login_digitado=login_digitado)

        id_usuario, nome, senha_hash, cargo, ativo = usuario

        # Caso 2: usuário existe, mas a senha não confere -> mensagem específica
        if not check_password_hash(senha_hash, senha_digitada):
            return render_template("login.html",
                                    erro="Senha incorreta.",
                                    login_digitado=login_digitado)

        # Login OK -> guarda dados essenciais na sessão
        session["id_usuario"] = id_usuario
        session["nome"] = nome
        session["cargo"] = cargo

        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/novo_usuario")
@login_required
@admin_required
def incluir_usuario():
    return render_template("novo_usuario.html")


@app.route("/salvar_usuario", methods=["POST"])
@login_required
@admin_required
def salvar_usuario():
    nome_completo = request.form.get("nome", "").strip()
    senha_numerica = request.form.get("senha", "").strip()
    cargo = "comum"

    partes = nome_completo.lower().split()
    base_login = f"{partes[0]}.{partes[-1]}" if len(partes) > 1 else partes[0]

    conexao = sqlite3.connect("monitoramento_condominios.db")
    cursor = conexao.cursor()

    login_final = base_login
    contador = 2
    while True:
        cursor.execute("SELECT 1 FROM usuarios WHERE login = ?", (login_final,))
        if not cursor.fetchone():
            break
        login_final = f"{base_login}{contador}"
        contador +=1

    senha_hash = generate_password_hash(senha_numerica)

    cursor.execute("""
        INSERT INTO usuarios (nome, login, senha_hash, cargo, precisa_trocar_senha, ativo)
        VALUES (?, ?, ?, ?, 1 , 1)
    """, (nome_completo, login_final, senha_hash, cargo))

    conexao.commit()
    conexao.close()

    return f"""
    <script>
        alert('Usuário cadastrado com sucesso! Login: {login_final}');
        window.location = '/';
    </script>
    """


# VERIFICAÇÃO AUTOMÁTICA DE ATRASOS (roda todo dia às 8h30)
def verificar_atrasos():
    conexao = sqlite3.connect("monitoramento_condominios.db")
    cursor = conexao.cursor()
    hoje = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT
            agendamento_servico.id_agendamento,
            condominios.nome_condominio,
            servicos.nome_servico
        FROM agendamento_servico
        JOIN condominios ON agendamento_servico.id_condominio = condominios.id_condominio
        JOIN servicos    ON agendamento_servico.id_servico    = servicos.id_servico
        WHERE agendamento_servico.data_servico < ?
          AND agendamento_servico.status_servico = 'Agendado'
    """, (hoje,))
    servicos_atrasados = cursor.fetchall()

    for servico in servicos_atrasados:
        mensagem = f"Serviço de {servico[2]} do Condomínio {servico[1]} entrou em atraso hoje."

        cursor.execute("""
            SELECT COUNT(*) FROM alertas
            WHERE mensagem = ? AND data_alerta = ?
        """, (mensagem, hoje))

        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO alertas (mensagem, data_alerta) VALUES (?, ?)
            """, (mensagem, hoje))

    cursor.execute("""
        UPDATE agendamento_servico
        SET status_servico = 'Atraso'
        WHERE data_servico < ?
          AND status_servico = 'Agendado'
    """, (hoje,))

    conexao.commit()
    conexao.close()
    print("✔ Verificação de atrasos executada:", datetime.now())


scheduler = BackgroundScheduler()
scheduler.add_job(verificar_atrasos, trigger='cron', hour=8, minute=30)


# PÁGINA PRINCIPAL
@app.route("/")
@login_required
def home():
    conexao = sqlite3.connect("monitoramento_condominios.db")
    cursor  = conexao.cursor()
    hoje    = datetime.now().strftime("%Y-%m-%d")

    # contadores dos cards
    cursor.execute("SELECT COUNT(*) FROM alertas WHERE date(data_alerta) = date(?)", (hoje,))
    alertas_dia = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM agendamento_servico WHERE status_servico = 'Finalizado'")
    finalizados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM agendamento_servico WHERE status_servico = 'Agendado'")
    agendados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM agendamento_servico WHERE status_servico = 'Atraso'")
    atrasados = cursor.fetchone()[0]

    # alertas apenas do dia atual
    cursor.execute("""
        SELECT mensagem, data_alerta FROM alertas
        WHERE date(data_alerta) = date(?)
        ORDER BY id_alerta DESC
    """, (hoje,))
    alertas = cursor.fetchall()

    # listas para os dropdowns de filtro
    cursor.execute("SELECT id_condominio, nome_condominio FROM condominios ORDER BY nome_condominio")
    lista_condominios = cursor.fetchall()

    cursor.execute("SELECT id_servico, nome_servico FROM servicos ORDER BY nome_servico")
    lista_servicos = cursor.fetchall()

    cursor.execute("SELECT id_prestador, nome_prestador FROM prestadores ORDER BY nome_prestador")
    lista_prestadores = cursor.fetchall()

    # captura dos filtros enviados pelo formulário
    filtro_os         = request.args.get("os", "").strip()
    filtro_condominio = request.args.get("condominio", "").strip()
    filtro_servico    = request.args.get("servico", "").strip()
    filtro_prestador  = request.args.get("prestador", "").strip()
    filtro_data       = request.args.get("data", "").strip()
    filtro_status     = request.args.get("status", "").strip()

    # query principal com filtros dinâmicos
    query = """
        SELECT
            agendamento_servico.id_agendamento,
            condominios.nome_condominio,
            servicos.nome_servico,
            prestadores.nome_prestador,
            agendamento_servico.data_servico,
            agendamento_servico.status_servico
        FROM agendamento_servico
        JOIN condominios ON agendamento_servico.id_condominio = condominios.id_condominio
        JOIN servicos    ON agendamento_servico.id_servico    = servicos.id_servico
        JOIN prestadores ON agendamento_servico.id_prestador  = prestadores.id_prestador
        WHERE 1=1
    """
    parametros = []

    if filtro_os:
        query += " AND agendamento_servico.id_agendamento = ?"
        parametros.append(filtro_os)

    if filtro_condominio:
        query += " AND agendamento_servico.id_condominio = ?"
        parametros.append(filtro_condominio)

    if filtro_servico:
        query += " AND agendamento_servico.id_servico = ?"
        parametros.append(filtro_servico)

    if filtro_prestador:
        query += " AND agendamento_servico.id_prestador = ?"
        parametros.append(filtro_prestador)

    if filtro_data:
        query += " AND agendamento_servico.data_servico = ?"
        parametros.append(filtro_data)

    if filtro_status:
        query += " AND agendamento_servico.status_servico = ?"
        parametros.append(filtro_status)

    query += " ORDER BY agendamento_servico.id_agendamento"

    cursor.execute(query, parametros)
    agendamentos = cursor.fetchall()

    conexao.close()

    return render_template(
        "index_v4.html",
        finalizados=finalizados,
        agendados=agendados,
        atrasados=atrasados,
        agendamentos=agendamentos,
        alertas=alertas,
        alertas_dia=alertas_dia,
        lista_condominios=lista_condominios,
        lista_servicos=lista_servicos,
        lista_prestadores=lista_prestadores,
        # devolve os valores para manter os filtros selecionados
        filtro_os=filtro_os,
        filtro_condominio=filtro_condominio,
        filtro_servico=filtro_servico,
        filtro_prestador=filtro_prestador,
        filtro_data=filtro_data,
        filtro_status=filtro_status,
    )


# ATUALIZAR STATUS
@app.route("/atualizar_status/<int:id_agendamento>/<novo_status>", methods=["POST"])
@login_required
def atualizar_status(id_agendamento, novo_status):
    conexao = sqlite3.connect("monitoramento_condominios.db")
    cursor  = conexao.cursor()

    if novo_status == "Agendado":
        nova_data = request.form.get("nova_data")
        cursor.execute("""
            UPDATE agendamento_servico
            SET status_servico = ?, data_servico = ?
            WHERE id_agendamento = ?
        """, (novo_status, nova_data, id_agendamento))
    else:
        cursor.execute("""
            UPDATE agendamento_servico
            SET status_servico = ?
            WHERE id_agendamento = ?
        """, (novo_status, id_agendamento))

    conexao.commit()
    conexao.close()

    return """
    <script>
        alert('Status atualizado com sucesso!');
        window.location.href = '/';
    </script>
    """


# INCLUIR SERVIÇO
@app.route("/novo_servico", methods=["GET", "POST"])
@login_required
def incluir_servico():
    conexao = sqlite3.connect("monitoramento_condominios.db")
    cursor  = conexao.cursor()

    cursor.execute("SELECT id_condominio, nome_condominio FROM condominios")
    condominios = pandas.DataFrame(cursor.fetchall(), columns=["id_condominio","nome_condominio"]).to_dict(orient="records")

    cursor.execute("SELECT id_servico, nome_servico FROM servicos")
    servicos = pandas.DataFrame(cursor.fetchall(), columns=["id_servico","nome_servico"]).to_dict(orient="records")

    cursor.execute("SELECT id_prestador, nome_prestador FROM prestadores")
    prestadores = pandas.DataFrame(cursor.fetchall(), columns=["id_prestador","nome_prestador"]).to_dict(orient="records")

    conexao.close()
    return render_template("/novo_servico.html", servicos=servicos, condominios=condominios, prestadores=prestadores)


# SALVAR SERVIÇO
@app.route("/salvar_servico", methods=["GET", "POST"])
@login_required
def salvar_servico():
    conexao = sqlite3.connect("monitoramento_condominios.db")

    if request.method == "POST":
        id_condominio  = request.form.get("condominio")
        id_prestador   = request.form.get("prestador")
        id_servico     = request.form.get("servico")
        data_servico   = str(request.form.get("data_servico"))
        status_servico = request.form.get("status")

        cursor = conexao.cursor()
        cursor.execute("SELECT MAX(id_agendamento) FROM agendamento_servico")
        id_agendamento = cursor.fetchone()[0] + 1

        cursor.execute("""
            INSERT INTO agendamento_servico
                (id_agendamento, id_condominio, id_servico, id_prestador, data_servico, status_servico)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id_agendamento, id_condominio, id_servico, id_prestador, data_servico, status_servico))

        conexao.commit()
        cursor.close()

    return """
    <script>
        alert('Serviço agendado com sucesso!');
        window.location.href = '/';
    </script>
    """


# CADASTRO DE TIPO DE SERVIÇO
@app.route("/novo_tipo_servico")
@login_required
def cadastro_tipo_servico():
    return render_template("/cadastro_tipo_servico.html")


# CADASTRO DE PRESTADOR
@app.route("/novo_prestador")
@login_required
def incluir_prestador():
    return render_template("cadastro_prestador.html")


@app.route("/salvar_prestador", methods=["GET", "POST"])
@login_required
def salvar_prestador():
    if request.method == "POST":
        nome_prestador = request.form.get("nome_prestador")
        telefone       = request.form.get("telefone")
        email          = request.form.get("email")
        especialidade  = request.form.get("especialidade")

        arquivo_excel = "1.Prestadores.xlsx"

        if os.path.exists(arquivo_excel):
            df_existente = pandas.read_excel(arquivo_excel)
            novo_id = int(df_existente["id_prestador"].max()) + 1 if len(df_existente) > 0 else 1
        else:
            df_existente = pandas.DataFrame(columns=["id_prestador","nome_prestador","telefone","email","especialidade"])
            novo_id = 1

        novo_registro = pandas.DataFrame([{
            "id_prestador": novo_id,
            "nome_prestador": nome_prestador,
            "telefone": telefone,
            "email": email,
            "especialidade": especialidade
        }])

        pandas.concat([df_existente, novo_registro], ignore_index=True).to_excel(arquivo_excel, index=False)

        return f"""
        <script>
            alert('Prestador cadastrado com sucesso! ID {novo_id}');
            window.location.href = '/';
        </script>
        """


# GET PRESTADORES POR SERVIÇO (Fetch API)
@app.route("/get_prestador/<int:id_servico>")
@login_required
def get_prestador(id_servico):
    conexao = sqlite3.connect("monitoramento_condominios.db")
    cursor  = conexao.cursor()

    cursor.execute("""
        SELECT p.id_prestador, p.nome_prestador, ps.id_servico
        FROM prestadores p
        INNER JOIN prestador_servico ps ON p.id_prestador = ps.id_prestador
        WHERE ps.id_servico = ?
    """, (id_servico,))

    prestadores = pandas.DataFrame(cursor.fetchall(), columns=["id_prestador","nome_prestador","id_servico"])
    conexao.close()

    return jsonify(prestadores.to_dict(orient="records"))


if __name__ == "__main__":
    scheduler.start()
    app.run(debug=True, use_reloader=False)
