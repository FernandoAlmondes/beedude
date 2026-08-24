#!/bin/bash

# Desenvolvido por: Bee Solutions
# Autor: Fernando Almondes
# Data: 18/02/2026 - 19:18

echo "---------------------------------------------------------------------------------"
echo ""
echo "--> Desenvolvido por: Bee Solutions"
echo "--> Autor: Fernando Almondes"
echo "--> Iniciando instalacao do Beedude Lite, por favor aguarde..."
echo ""
echo "---------------------------------------------------------------------------------"

# Instalacao das dependencias do Linux
apt -y install python3-venv redis-server nginx

# Indo ate o diretorio base do projeto
cd /opt/bee/beedude

# Instalacao do python3.11
p=$(which python3.11)
if [[ -z "$p" ]]; then
    echo "Python 3.11 nao encontrado, fazendo a instalacao."
    apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev libxml2-dev libxslt1-dev
    cd ~ && wget https://www.python.org/ftp/python/3.11.13/Python-3.11.13.tar.xz
    tar xvf Python-3.11.13.tar.xz && cd Python-3.11.13
    ./configure --enable-optimizations --with-ensurepip=install
    make -j $(nproc) && make altinstall

    # Removendo arquivo temporarios
    rm -rf ~/Python-3.11.13
    rm ~/Python-3.11.13.tar.xz
fi

# Voltando ao diretorio base
cd /opt/bee/beedude

# Subindo ambiente venv
python3.11 -m venv venv

# Ativando venv
source venv/bin/activate

# Instalacao das dependencias do python
pip install django django-redis httpx gunicorn humanize python-decouple

# Criacao arquivo .env com a chave para o settings.py
python3 beedude-chave.py > /opt/bee/beedude/beesoft/.env

# Ajustando arquivo settings.py
mv /opt/bee/beedude/beesoft/settings.exemplo /opt/bee/beedude/beesoft/settings.py

# Povoando banco de dados padrao
python3 manage.py makemigrations
python3 manage.py migrate

# Criacao do usuario padrao
export DJANGO_SUPERUSER_USERNAME=beesoft
export DJANGO_SUPERUSER_EMAIL=beesoft@example.com
export DJANGO_SUPERUSER_PASSWORD=beesoft
python3 manage.py createsuperuser --noinput

# Criando dados padroes
python3 beedude-base-bd.py

# Criacao do usuario bee no Linux
useradd -r -d /opt/bee/ -s /usr/sbin/nologin beesolutions

# Ajustando permissoes do diretorio bee
chown -R beesolutions:beesolutions /opt/bee/beedude

# Criando servico do Beedude
mv /opt/bee/beedude/beedude-server.service /etc/systemd/system/

# Iniciando servico do Beedude
systemctl daemon-reload

systemctl start beedude-server.service
systemctl enable beedude-server.service

# Ajustando o nginx
unlink /etc/nginx/sites-enabled/default

echo '''
server {
    listen 9000;
    server_name beedude.seudominio.com.br;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /opt/bee/beedude;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/opt/bee/beedude/beedude-server.sock;
    }
}
''' > /etc/nginx/sites-enabled/beedude.seudominio.com.br

# Coletando arquivos estaticos
python3 manage.py collectstatic

nginx -t
service nginx restart

# Restartando servico ao finalizar
systemctl restart beedude-server.service

# Verificando status do servico
systemctl status beedude-server.service

echo ""
echo "---------------------------------------------------------------------------------"
echo ""
echo "--> Instalacao do Beedude Finalizada..."
echo "--> Acesse via o seu http://seu-ip:9000."
echo "--> Usuario padrao: beesoft"
echo "--> Senha padrao: beesoft"
echo ""
echo "---------------------------------------------------------------------------------"