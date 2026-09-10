# Sistema de Gestão de Manutenção (FSM) para Condomínios

Sistema web para gerenciamento de ordens de serviço de manutenção em múltiplos condomínios, com controle de prestadores, tipos de serviço, agendamento e monitoramento automático de atrasos (SLA).

Desenvolvido para uso real em uma empresa que atende dezenas de condomínios, atualmente em fase de implantação.

## 🎯 O problema que o sistema resolve

Empresas que administram manutenção predial para múltiplos condomínios lidam com um volume grande de prestadores externos, tipos de serviço diferentes e prazos que precisam ser acompanhados manualmente. Esse sistema centraliza esse controle, elimina planilhas soltas e gera alertas automáticos quando um serviço está atrasado.

## ⚙️ Funcionalidades

- Cadastro de condomínios, prestadores de serviço e tipos de serviço
- Agendamento de ordens de serviço com status (Agendado, Em Andamento, Finalizado, Atrasado)
- Seleção dinâmica de prestadores por tipo de serviço (via requisição assíncrona / Fetch API)
- Autenticação com controle de acesso por papel (Admin / Usuário comum)
- Verificação automática diária de atrasos (job em background com APScheduler), com geração de alertas
- Senhas armazenadas com hash (nunca em texto puro)

## 🛠️ Tecnologias utilizadas

- **Backend:** Python, Flask
- **Banco de dados:** SQLite
- **Frontend:** HTML, CSS, JavaScript (Fetch API), templates Jinja2
- **Autenticação/Segurança:** Werkzeug (hash de senha), variáveis de ambiente (`python-dotenv`)
- **Automação:** APScheduler (agendamento de tarefas em background)

## 🚀 Como rodar localmente

1. Clone o repositório:
```bash
   git clone https://github.com/ma7ferreira/meu_projeto_fsm.git
   cd meu_projeto_fsm
```

2. Instale as dependências:
```bash
   pip install -r requirements.txt
```

3. Crie um arquivo `.env` na raiz do projeto com:

SECRET_KEY=uma-chave-aleatoria-de-sua-escolha


4. Rode o script de criação do usuário administrador (uma única vez):
```bash
   python criar_admin_master.py
```

5. Inicie a aplicação:
```bash
   python app_v1.py
```

6. Acesse `http://localhost:5000` no navegador.

## 🗺️ Status do projeto e próximos passos

Este sistema está atualmente em fase de finalização e será implantado em produção em uma empresa real que atende cerca de 44 condomínios.

Próximas etapas planejadas:
- [ ] Implantação e testes em ambiente real de produção
- [ ] Após alguns meses de uso (acúmulo de dados reais de ordens de serviço), desenvolvimento de uma camada de **análise de dados** sobre o histórico gerado — como identificação de padrões de atraso por prestador, tipo de serviço ou condomínio
- [ ] Possível evolução para um modelo preditivo simples de risco de atraso de OS

## 📌 Observação sobre os dados

Este repositório contém uma versão sanitizada do projeto: nomes de empresa, credenciais reais e dados de produção foram removidos ou substituídos por valores genéricos, mantendo apenas a estrutura e lógica do sistema.

## 👤 Autor

[Marina Ferreira]
[LinkedIn] (https://www.linkedin.com/in/marina-f-oliveira5/)