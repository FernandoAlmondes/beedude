import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beesoft.settings')
django.setup()

from beeapi.models import Mapa, Servidor, Node, Edge

# Criando base para a instalacao
server = Servidor.objects.create(nome='Servidor-Bee-01', url='http://192.168.0.10/zabbix/api_jsonrpc.php', token='12345', status=True)
mapa = Mapa.objects.create(nome='Mapa-Bee-01', default='True', servidor=server, autor_id=1)

node1 = Node.objects.create(nome='Router-Bee-01', mapa=mapa)
node2 = Node.objects.create(nome='Router-Bee-02', mapa=mapa)

edge = Edge.objects.create(nome='node1-e-node2', source=node1, target=node2, mapa=mapa)


