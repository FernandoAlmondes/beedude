import os
import csv
from time import sleep
import psycopg2
import django
from decouple import config

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "beedude.settings")
django.setup()

from grafo.models import Elemento, Item

# Linux
os.makedirs('/opt/bee/beedude/tmp', exist_ok=True)
tmp = os.path.join('opt', 'bee', 'beedude', 'tmp')

# Windows
#os.makedirs('tmp', exist_ok=True)
#tmp = os.path.join('tmp')

print('---> Desenvolvido por: Bee Solutions')
print('---> Autor: Fernando Almondes')
print('---> Sistema: Beedude')

elementos = list(Elemento.objects.all().values())

def conecta_zabbix_hosts():
    print('--> Iniciando conexao com o banco de dados do Zabbix (Tabela de Hosts)...')

    # Configurações de conexão com o banco de dados MySQL
    conexao_banco = {
        'host': config('DB_HOST_ZABBIX'),
        'port': config('DB_PORT_ZABBIX'),
        'database': config('DB_NAME_ZABBIX'),
        'user': config('DB_USER_ZABBIX'),
        'password': config('DB_PASSWORD_ZABBIX')
    }

    # Consulta SQL
    consulta_sql = f'''
        select ht.name host, ht.hostid,it.name item, it.itemid ,hu.value status,TO_TIMESTAMP(hu.clock) horario,concat('1') as node from items it 
        inner join hosts ht on (it.hostid = ht.hostid)
        inner join hosts_groups hg on (hg.hostid = ht.hostid)
        inner join hstgrp hst on (hst.groupid = hg.groupid)
        inner join (select itemid, max(clock) as max_clock from history_uint group by itemid) as max_hu on max_hu.itemid = it.itemid
        inner join history_uint hu on (hu.itemid = max_hu.itemid and max_hu.max_clock = hu.clock)
        where it.hostid in (select hostid from hosts where status = 0 and flags = 0) and it.key_ = 'icmpping' and hst.name in ('BEEDUDE')
        group by it.itemid, ht.name, ht.hostid, it.name, it.itemid, hu.value, horario, node;
    '''

    # Nome do arquivo CSV para salvar os resultados
    nome_arquivo_csv = f'/{tmp}/tabela_hosts.csv'

    # Conectar ao banco de dados
    try:
        conexao = psycopg2.connect(**conexao_banco)
        cursor = conexao.cursor()
        cursor.execute(consulta_sql)

        # Obter resultados da consulta
        resultados = cursor.fetchall()

        # Salvar resultados em um arquivo CSV
        with open(nome_arquivo_csv, 'w', newline='', encoding='utf-8') as arquivo_csv:
            colunas = [desc[0] for desc in cursor.description] if resultados else []
            escritor_csv = csv.writer(arquivo_csv)

            # Escrever cabeçalho
            escritor_csv.writerow(colunas)

            # Escrever dados
            escritor_csv.writerows(resultados)

        # print(f"Resultados salvos em {nome_arquivo_csv}")

    except psycopg2.Error as erro:
        print(f"Erro ao conectar ao banco de dados: {erro}")

    finally:
        # Fechar cursor e conexão
        if 'cursor' in locals() and cursor:
            cursor.close()

        if 'conexao' in locals() and conexao:
            conexao.close()


def conecta_zabbix_items():
    print('--> Iniciando conexao com o banco de dados do Zabbix (Tabela de Items)...')

    # Configurações de conexão com o banco de dados MySQL
    conexao_banco = {
        'host': config('DB_HOST_ZABBIX'),
        'port': config('DB_PORT_ZABBIX'),
        'database': config('DB_NAME_ZABBIX'),
        'user': config('DB_USER_ZABBIX'),
        'password': config('DB_PASSWORD_ZABBIX')
    }

    # Consulta SQL
    consulta_sql = '''
        select ht.hostid as hostid,ht.name as host,it.itemid as itemid,it.name as item,
        coalesce(hu.value, 0) as valor,
        concat(CASE WHEN (it.name like '%status%' or it.name like '%Link down%') THEN coalesce(hu.value, '0') ELSE '0' END) AS status,
        coalesce(TO_TIMESTAMP(hu.clock), '2000-01-01 00:00:00') as horario
        from items it
        inner join hosts ht on (ht.hostid = it.hostid)
        inner join hosts_groups hg on (hg.hostid = ht.hostid)
        inner join hstgrp hst on (hst.groupid = hg.groupid)
        left join (select itemid, max(clock) as max_clock from history_uint group by itemid) AS max_hu ON max_hu.itemid = it.itemid
        left join history_uint hu on hu.itemid = max_hu.itemid and hu.clock = max_hu.max_clock
        where (it.name like '%Bits r%' or it.name like '%Bits s%' or it.name like '%gei_%' or it.name like '%status%')
        and it.name not like ('%IFALIAS%')
        and it.name not like '%Vlan%' and it.name not like '%vlan%'
        and it.name not like '%{#IFNAME}%' and it.name not like '%{#SNMPVALUE}%' and it.name not like '%Fan%'
        and ht.status = 0 and ht.flags != 2 and it.status = 0 and hst.name in ('BEEDUDE');
    '''

    # Nome do arquivo CSV para salvar os resultados
    nome_arquivo_csv = f'/{tmp}/tabela_items.csv'

    # Conectar ao banco de dados
    try:
        conexao = psycopg2.connect(**conexao_banco)
        cursor = conexao.cursor()
        cursor.execute(consulta_sql)

        # Obter resultados da consulta
        resultados = cursor.fetchall()

        # Salvar resultados em um arquivo CSV
        with open(nome_arquivo_csv, 'w', newline='', encoding='utf-8') as arquivo_csv:
            colunas = [desc[0] for desc in cursor.description] if resultados else []
            escritor_csv = csv.writer(arquivo_csv)

            # Escrever cabeçalho
            escritor_csv.writerow(colunas)

            # Escrever dados
            escritor_csv.writerows(resultados)

        # print(f"Resultados salvos em {nome_arquivo_csv}")

    except psycopg2.Error as erro:
        print(f"Erro ao conectar ao banco de dados: {erro}")

    finally:
        # Fechar cursor e conexão
        if 'cursor' in locals() and cursor:
            cursor.close()

        if 'conexao' in locals() and conexao:
            conexao.close()


def importa_edges():
    csv_file_path = f'/{tmp}/lista-hosts-edges.csv'

    with open(csv_file_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file, delimiter=';')
        for row in csv_reader:
            print(row)

            def get_elemento_instance(codigo):
                try:
                    return Elemento.objects.get(codigo=codigo)
                except Elemento.DoesNotExist:
                    return None

            try:
                host_a_instance = get_elemento_instance(row['host_a'])
            except KeyError:
                host_a_instance = None

            try:
                host_b_instance = get_elemento_instance(row['host_b'])
            except KeyError:
                host_b_instance = None

            item, created = Elemento.objects.update_or_create(
                codigo=['hostid'],
                defaults={
                    'codigo': row['codigo'],
                    'label': row['label'],
                    'status': row['status'],
                    'node': row['node'],
                    'host_a': host_a_instance,
                    'host_b': host_b_instance,
                }
            )


def importa_hosts():
    print('--> Importando atualizacao dos hosts...')
    csv_file_path = f'/{tmp}/tabela_hosts.csv'

    with open(csv_file_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file, delimiter=',')
        for row in csv_reader:
            item, created = Elemento.objects.update_or_create(
                codigo=int(row['hostid']),
                defaults={
                    'codigo': int(row['hostid']),
                    'label': row['host'],
                    'status': row['status'],
                    'node': 1,
                    'horario': row['horario'],

                }
            )


def importa_items():
    print('--> Importando atualizacao dos items...')
    csv_file_path = f'/{tmp}/tabela_items.csv'

    with open(csv_file_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file, delimiter=',')
        for row in csv_reader:
            item, created = Item.objects.update_or_create(
                itemid=int(row['itemid']),
                defaults={
                    'itemid': int(row['itemid']),
                    'nome': row['host'] + ' | ' + row['item'],
                    'status': row['status'] if row['status'] != 'NULL' else 1,
                    'valor': row['valor'] if row['valor'] != 'NULL' and row['valor'] != '' else 0,
                    'horario': row['horario'] if row['valor'] != 'NULL' and row['valor'] != '' else '2000-01-01 00:00:00',

                }
            )


def executa_atualizacao():
    while (True):
        print('--> Atualizando dados...')
        conecta_zabbix_hosts()
        conecta_zabbix_items()
        importa_hosts()
        importa_items()
        print('\n--------------------------------------------------------------------')
        print('\n--> Aguardando 10 segundos ate a nova consulta...')
        print('\n--------------------------------------------------------------------')
        sleep(10)

executa_atualizacao()