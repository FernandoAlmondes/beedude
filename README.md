### --> Beesoft 1.0 (By: Bee Solutions) <-- ###
### Módulo Beedude ✅ ###
--- ---
# Projeto destinado ao monitoramento de ativos e redes backbone usando mapas de hosts (Integrado ao Zabbix)
- Python, Django, Javascript e Zabbix
--- ---
- Sobre o projeto:
> - Desenvolvido por: Bee Solutions
> - Autor: Fernando Almondes
> - Principais ferramentas: Python, Django e Zabbix
> - Novidade: Agora 100% open-source ;)
--- ---

- Distribuições homologados (Sistemas Operacionais Linux Server)
> - Ubuntu Server 22.04 LTS (Ou superior)
> - Debian 12 (Ou Superior)
> - PgSQL e MySQL
> - Zabbix 5.x e Zabbix 6.x

--- ---

- Funcionalidades do Beedude (Versão 1.0 Free):
> - Hosts ilimitados (Disponível ✅)
> - Status dos hosts (Disponível ✅) 
> - Status da interface que liga os hosts (Disponível ✅)
> - Tráfego de in e out da interface que liga os hosts (Disponível ✅)
> - Integração com Zabbix (Disponível ✅)
> - Atualização em tempo real (Disponível ✅)
> - Cadastro dos hosts e itens automático (Disponível ✅)
> - Mapas ilimitados (Disponível ✅)
> - Painel de administração para cadastro das conexões entre os hosts (Disponível ✅)
--- ---

# 1# Dashboard de exemplo | Backbone Beedude

![Painel](https://beesolutions.com.br/static/beedude/public/img/beedude-topologia-apresentacao-01.png)
--- ---

# 2# Dashboard de exemplo | Backbone Beedude

![Painel](https://beesolutions.com.br/static/beedude/public/img/beedude-topologia-apresentacao-04.png)
--- ---

# Parte 1 - Instalação do Beedude #
--- ---

- Crie o diretorio base para o projeto (BeesoftPro).
```shell
mkdir /opt/bee/
```

- Navegue até o diretorio base do projeto.
```shell
cd /opt/bee/
```

- Faça download do código fonte via Git Clone.
```shell
git clone https://github.com/FernandoAlmondes/beedude.git
```

- Entre no diretorio do projeto.
```shell
cd /opt/bee/beedude
```

# Parte 2.1 - Ubuntu Server 20.x LTS ou 22.x LTS #

- Faça a instalação das dependencias do Linux no projeto
```shell
add-apt-repository ppa:deadsnakes/ppa 
apt-get update
apt-get install python3.11 python3.11-dev default-libmysqlclient-dev build-essential libpq-dev pkg-config
```

# Parte 2.2 - Debian 12 #
- Faça a instalação das dependencias do Linux no projeto
```shell
apt-get update
apt-get install python3.11 python3.11-dev default-libmysqlclient-dev build-essential sudo pkg-config libpq-dev
```

- O Debian 12 já vem com o python 3.11 instalado (Recomendado), então prossiga...
- Caso esteja usando Debian 11, pode seguir sempre utilizando "python3-x" que vai funcionar da mesma forma...


# Parte 3 - Ambiente virtual e banco de dados #

- Instate o venv para gerenciar ambientes virtuais com Python.
```shell
apt install python3.11-venv
```

- Crie um novo ambiente virtual Python.
```shell
python3.11 -m venv venv
```

- Ative o seu ambiente virtual.
```shell
source venv/bin/activate
```

- Instale as dependencias do projeto.
```shell
pip install -r dependencias.txt
```

- Criando database e usuarios do banco de dados (MySQL).
```shell
mysql -u root -p
```
```shell
mysql> create database beesoft_db_01 character set utf8mb4 collate utf8mb4_bin;
mysql> create user beesoftadmin@localhost identified by 'AQUI-VOCE-COLOCA-SUA-SUPER-SENHA-PRA-APLICACAO';
mysql> grant all privileges on beesoft_db_01.* to beesoftadmin@localhost;

mysql> create user beesoftconsultor@localhost identified by 'AQUI-VOCE-COLOCA-UMA-SENHA-BOA';
mysql> grant SELECT on beesoft_db_01.* to beesoftconsultor@localhost;
mysql> quit
```
--- ---

- Criando database e usuarios do banco de dados (PgSQL).
```shell
sudo -u postgres createuser --pwprompt beesoftadmin
sudo -u postgres createdb -O beesoftadmin beedude_db_01
```
- Criando usuário de visualização para o banco de dados do Zabbix (PgSQL).

```shell
sudo -u postgres psql

postgres=\# \c zabbix
zabbix=\# CREATE USER beesoftconsultor WITH PASSWORD 'AQUI-VOCE-COLOCA-UMA-SENHA-BOA';
zabbix=\# GRANT SELECT ON ALL TABLES IN SCHEMA public TO beesoftconsultor;
zabbix=\# \q
```
--- ---

- Gere uma chave de segurança para usar no seu settings.py (Guarde essa chave, você a usará em seguida).
```shell
python /opt/bee/beedude/chave.py
```

- Renomei o seu arquivo settings.exemplo para settings.py.
```shell
mv /opt/bee/beedude/beedude/settings.exemplo /opt/bee/beedude/beedude/settings.py
```

- Renomei o arquivo .env e preencha as informações a seguir.
```shell
mv /opt/bee/beedude/beedude/.env.exemplo /opt/bee/beedude/beedude/.env
```
- Ajuste o arquivo .env e preencha as informações corretamente, secret_key, database, usuario e senha da aplicação.
```shell
nano /opt/bee/beedude/beedude/.env
```
```shell
############# DADOS APLICACAO ##############
SECRET_KEY=SUA-CHAVE-SECRETA-AQUI
FERNET_KEY=SUA-FERNET-KEY-AQUI
DEBUG=True
ALLOWED_HOSTS=127.0.0.1, localhost, beedude.meudominio.com.br
DB_NAME=beedude_db_01
DB_USER=beesoftadmin
DB_PASSWORD=SENHA-BANCO-DE-DADOS-ADMIN
DB_HOST=127.0.0.1
DB_PORT=3306
## ALTERE PARA 5432 se POSTGRES
##############################################

############# DADOS ZABBIX ##############
DB_NAME_ZABBIX=zabbix
DB_USER_ZABBIX=beesoftconsultor
DB_PASSWORD_ZABBIX=SENHA-BANCO-DE-DADOS-LEITURA-ZABBIX
DB_HOST_ZABBIX=127.0.0.1
DB_PORT_ZABBIX=3306
## ALTERE PARA 5432 se POSTGRES
#########################################

############# LICENCA BEEDUDE ##############
LICENCA_BEEDUDE_KEY=INSIRA-SUA-LICENCA-AQUI-SE-TIVER-UMA
#########################################
```

```shell
nano /opt/bee/beedude/beedude/settings.py
```
- Renomei o nome do banco para "default" de acordo com o que voce tiver utilizando (mysql -> default ou pgsql -> default)
```shell
# Exemplo Mysql
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    },'pgsql': {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config('DB_NAME'),
        "USER": config('DB_USER'),
        "PASSWORD": config('DB_PASSWORD'),
        "HOST": config('DB_HOST'),
        "PORT": config('DB_PORT'),
    }
}
-
# Exemplo Postgres
DATABASES = {
    'mysql': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    },'default': {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config('DB_NAME'),
        "USER": config('DB_USER'),
        "PASSWORD": config('DB_PASSWORD'),
        "HOST": config('DB_HOST'),
        "PORT": config('DB_PORT'),
    }
}
```

- Realizando teste no servidor Django.
```shell
python manage.py runserver
```
```shell
# Exemplo de resultado esperado:
(venv) root@bee:/opt/bee/beedude# python manage.py runserver
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).

You have 21 unapplied migration(s). Your project may not work properly until you apply the migrations for app(s): admin, auth, contenttypes, painel, sessions.
Run 'python manage.py migrate' to apply them.
May 20, 2023 - 00:54:57
Django version 4.2.1, using settings 'beedude.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

- Validando integração com o banco de dados.
```shell
python manage.py makemigrations
python manage.py migrate
```

# Parte 4 - Preparando aplicação #

- Criando superusuario (Aqui você cria o usuário para acessar o Admin).
```shell
python manage.py createsuperuser
```

- Agora libere o IP do seu servidor no .env (Ou dominio caso deseje acessar via domino, no lugar de IP).
```shell
nano /opt/bee/beedude/beedude/.env
```
```shell
ALLOWED_HOSTS=IP-DO-SEU-SERVIDOR-AQUI
```

- Inicie novamente o servidor e tente acessar o django admin via Web.
```shell
python manage.py runserver IP-DO-SEU-SERVIDOR:5000
```
- Acesso a página inicial (Teste).
```shell
http://IP-DO-SEU-SERVIDOR:5000/
```
- Acesso ao Admin (Gerencia das tabelas e usuários do sistema).
```shell
http://IP-DO-SEU-SERVIDOR:5000/admin
```

# Parte 5 - Fazendo o deploy da aplicação usando Nginx, Gunicorn e Certbot  #

- Criando socket (Será usado no proxy reverso com Nginx).
```shell
nano /etc/systemd/system/beedude-server.socket
```
```shell
[Unit]
Description=Beedude socket

[Socket]
ListenStream=/run/beedude-server.sock

[Install]
WantedBy=sockets.target
```

- Criando serviço para execução em segundo plano do beedude-server.
```shell
nano /etc/systemd/system/beedude-server.service
```
```shell
[Unit]
Description=Beedude daemon
Requires=beedude-server.socket
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/opt/bee/beedude
ExecStart=/opt/bee/beedude/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/beedude-server.sock \
          beedude.wsgi:application

[Install]
WantedBy=multi-user.target

```

- Criando serviço para execução em segundo plano do beedude-agente (Ajuste para beedude-agente-pgsql.py se Postgres).
```shell
nano /etc/systemd/system/beedude-agente.service
```
```shell
[Unit]
Description=Beedude Agente

[Service]
ExecStart=/opt/bee/beedude/venv/bin/python /opt/bee/beedude/beedude-agente-mysql.py
#ExecStart=/opt/bee/beedude/venv/bin/python /opt/bee/beedude/beedude-agente-pgsql.py
Restart=always
User=root
Group=root

[Install]
WantedBy=default.target
```

- Instalando Nginx (Se você já tiver o apache2 rodando ajuste as portas).
```shell
apt install nginx
```

- Desative ou remova o link simbolico default do Nginx (Ou você pode ter conflito na porta 80, caso tenha o apache2 instalado).
```shell
unlink /etc/nginx/sites-enabled/default
```

- Criando servidor web com o Nginx.
```shell
nano /etc/nginx/sites-enabled/beedude.seudominio.com.br
```
```shell
server {
    listen 5000;
    server_name beedude.seudominio.com.br;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /opt/bee/beedude;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/beedude-server.sock;
    }
}
```

- Coletando arquivos estaticos.
```shell
python manage.py collectstatic
```

- Protegendo a aplicação com Certbot e Let's Encrypt (Recomendado).
- Instalando o Certbot.
```shell
apt install certbot python3-certbot-nginx
```
- Adicionando novo certificado SSL
```shell
certbot --nginx -d beedude.seudominio.com.br
```

- Iniciando e verificando serviços necessários.
```shell
systemctl daemon-reload

systemctl start beedude-server.socket beedude-server.service beedude-agente.service

nginx -t
service nginx restart

```

- Habilitando inicialização junto so boot dos serviços.
```shell
systemctl enable beedude-server.socket beedude-server.service beedude-agente.service
```

- Após validação, lembre-se de desativar o modo debug no arquivo .env e reiniciar a aplicação.
```shell
nano /opt/bee/beedude/beedude/.env
```
```shell
DEBUG=False
```
- Reiniciando serviços após desativar o modo Debug.
```shell
systemctl restart beedude-server.socket beedude-server.service beedude-agente.service 

service nginx restart
```

### Parte 6 - Configurando os Hosts no Zabbix ###

- Configure os hosts do backbone no grupo "BEEDUDE".
- Radical de nome de item suportado: "Bits r" ou "Bits s" para items de trafego.
- Radical de nome de item suportado: "status" para items de status de interface.

### Parte 7 - Configurando os Mapas no Django Admin ###
- Acesse o Djngo Admin e crie um novo Mapa.
- Após criar um novo mapa, vá até elementos e selecione todos os hosts e clique na opção "Editar em lote", marque mapa e vincule o mapa aos seus hosts. 
- Nesse momemto você já pode visualizar os hosts no mapa.
- Após isso volte ao Django Admin e crie as ligações conforme demonstrei no vídeo de apresentação.

#### - Exemplo de cadastro de Elementos (Lembrando que os nodes são cadastrados automaticamente pelo agente)
![Painel](https://beesolutions.com.br/static/beedude/public/img/beedude-exemplo-cadastro-elementos-e-ligacoes2.png)

#### - Lembre-se de cadastrar um servidor para que o clique dos nodes direcione para o seu servidor Zabbix
![Painel](https://beesolutions.com.br/static/beedude/public/img/beedude-exemplo-cadastro-url-zabbix.png)
--- ---


### Parte 8 - Precisa de suporte adicional? ###
- [Contato Comercial](https://t.me/fernandoalmondes)

### Parte 9 - Comunidade no Telegram e canal do YouTube ###

- [Comunidade no Telegram](https://t.me/beesolutions)
- [Canal no Youtuve](https://www.youtube.com/beesolutions)

> Participe e colabore com nossos projetos (Bee Solutions 2024).

### Parte 10 - Participe do nosso grupo Pro e contribua com a comunidade ###

📌 Faça parte do canal exclusivo com conteúdos adicionais e atualizados em primeira mão. 📌

Valor da Assinatura: R$9,99

Opções de assinatura (Canal Bee Solutions Pro):

Opção 01 - Mercado Pago
https://abre.ai/beesolutions

Opção 02 - Mercado Pago Anual (Desconto de -17%)
https://abre.ai/beeproanual

Opção 03 - Hotmart
https://hotm.art/beepromensal

Opção 04 - Hotmart Anual (Desconto de -17%)
https://hotm.art/beeproanual

--- ---
