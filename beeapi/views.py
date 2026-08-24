from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required

from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest

from django.core.paginator import Paginator

from .models import Mapa, Node, Edge, Servidor

from .forms import formAddMapa, formAddNode, formAddEdge

import json
import humanize
import re
import httpx
import secrets
from asgiref.sync import sync_to_async, async_to_sync

from django.core.cache import cache
from django.db.models import Q

from datetime import timedelta, datetime as dt

# Create your views here.

def tem_permissao(mapa, request):

    if request.user.is_superuser:
        mapas_no_grupo_do_usuario = Mapa.objects.all()
    else:
        mapas_no_grupo_do_usuario = Mapa.objects.filter(grupos_mapas__grupo__in=request.user.groups.all()).distinct()

    if mapa in mapas_no_grupo_do_usuario:
        return True

    return False

# Pagina principal
def index(request):
    # Verificando o que posso usar do usuario vindo no request
    #print(dir(request.user))

    # Definindo o mapa default como primeiro a aparecer
    if request.user.is_superuser:
        mapa = Mapa.objects.filter(default=True).first()
        if not mapa:
            mapa = Mapa.objects.all().first()
    else:
        mapa = Mapa.objects.filter(grupos_mapas__grupo__in=request.user.groups.all(), default=True).distinct().first()
        if not mapa:
            mapa = Mapa.objects.filter(grupos_mapas__grupo__in=request.user.groups.all()).distinct().first()

    dados = {
        'elementos': [],
        'mapa': mapa
    }

    return render(template_name='beeapi/index.html', context=dados, request=request)

# Retorna os dados para o mapa via API json
def dados(request, mapaid):
    nodes = list(Node.objects.filter(mapa_id=mapaid).values())
    edges = list(Edge.objects.filter(mapa_id=mapaid).values())

    #print('Nodes:', nodes)

    servidor = get_object_or_404(Servidor, mapa=mapaid)
    servidorid = servidor.id

    mapa = Mapa.objects.get(id=mapaid)

    #print('Permisao:', permissao)
    #print('Grupos do usuario:', list(request.user.groups.all().values()))

    if not tem_permissao(mapa=mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao para consultar esse mapa.')
    
    permissao = None

    if request.user.has_perm('beeapi.view_mapa'):
        permissao = 'view'
    if request.user.has_perm('beeapi.change_mapa'):
        permissao = 'edit'

    if not permissao:
        return HttpResponseForbidden('Voce nao tem permissao para visualizar mapas.')
        
    #print('Mapa:', mapaid)
    #print('Servidor:', servidorid)

    # Para o cytoscape o id nao pode ser igual entre node e edge (como no django sao tabelas separadas vamos usar um uuid)
    # Mesmo assim vamos passar o id original como nodeid e edgeid

    # Vou criar um mecanismo pra consultar todos os itens de uma vez em uma unica consulta

    def retorna_itens_triggers(eles):
        # Analisando itens dos nodes
        itens = [i['indicador']['itens'] for i in eles if i['indicador']]
        itens = [i for j in itens for i in j]
        res_its = []
        res_its = async_to_sync(itens_teste)(its=itens, id=servidorid) # Usamos o async_to_sync para poder rodar funcoes asyncronas dentro de funcoes sicronas.
        itens_dc = {}
        if res_its:
            itens_dc = {i['itemid']: i for i in res_its}

        # Analisando triggers dos nodes
        triggers = [i['indicador']['triggers'] for i in eles if i['indicador']]
        triggers = [i for j in triggers for i in j]
        res_tgs = []
        res_tgs = async_to_sync(triggers_teste)(tgs=triggers, id=servidorid) # Usamos o async_to_sync para poder rodar funcoes asyncronas dentro de funcoes sicronas.
        triggers_dc = {}
        if res_tgs:
            triggers_dc = {i['triggerid']: i for i in res_tgs}

        return itens_dc, triggers_dc

    nodes_itens_dc, nodes_triggers_dc = retorna_itens_triggers(nodes)
    edges_itens_dc, edges_triggers_dc = retorna_itens_triggers(edges)

    for i in nodes:
        #print('itens:', i['indicador']['itens'])
        i['idbd'] = i['id']
        i['id'] = i['nodeid']
        i['nodeid'] = i['idbd']
        if isinstance(i['indicador'], (dict)) and 'itens' in i['indicador']:
            # Usamos o async_to_sync para poder rodar funcoes asyncronas dentro de funcoes sicronas.
            try:
                its = [nodes_itens_dc.get(i) for i in i['indicador'].get('itens') if i]
                i['label'] = render_label(indicadores = its, template=i['label_template']) # Tenho que consultar a api do zbx
            except Exception as e:
                print(f'Erro ao processar labels {i}, itens existem no Zabbix (nodes)? {e}')

        if isinstance(i['indicador'], (dict)) and 'triggers' in i['indicador']:
            tgs = [nodes_triggers_dc.get(i) for i in i['indicador'].get('triggers') if i]
            i['status'] = valida_status(indicadores = tgs, modo=i['indicador']['modo']) # Tenho que consultar a api do zbx

        # Adicionando valor default caso nao tenha label
        try:
            i['label']
        except:
            i['label'] = i['label_template']

        # Adicionando valor default caso nao tenha status
        try:
            i['status']
        except:
            i['status'] = 'erro'

    for i in edges:
        i['source'] = i.pop('source_id')
        i['target'] = i.pop('target_id')
        i['idbd'] = i['id']
        i['id'] = i['edgeid']
        i['edgeid'] = i['idbd']
        if isinstance(i['indicador'], (dict)) and 'itens' in i['indicador']:
            try:
                its = [edges_itens_dc.get(i) for i in i['indicador'].get('itens') if i]
                i['label'] = render_label(indicadores = its, template=i['label_template']) # Tenho que consultar a api do zbx
            except Exception as e:
                print(f'Erro ao processar labels {e}, itens existem no Zabbix (edges)? {e}')
        if isinstance(i['indicador'], (dict)) and 'triggers' in i['indicador']:
            tgs = [edges_triggers_dc.get(i) for i in i['indicador'].get('triggers') if i]
            i['status'] = valida_status(indicadores = tgs, modo=i['indicador']['modo']) # Tenho que consultar a api do zbx

        # Adicionando valor default caso nao tenha label
        try:
            i['label']
        except:
            i['label'] = ''

        # Adicionando valor default caso nao tenha status
        try:
            i['status']
        except:
            i['status'] = 'erro'

    elementos = {}
    elementos['nodes'] = []
    elementos['edges'] = []
    elementos['permissao'] = permissao

    for i in nodes:
        elementos['nodes'].append({'data': i, 'position': {'x': i['x'], 'y': i['y']}, 'classes': [i['classe']]})
    
    for i in edges:
        elementos['edges'].append({'data': i})

    mapa.data = elementos
    mapa.save()

    dados = {
        'elementos': json.dumps(elementos)
    }

    #return render(template_name='beeapi/mapa.html', request=request, context=dados)
    return JsonResponse(elementos, safe=False)

def listaMapa(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    #print('Permissoes do usuario:', request.user.get_all_permissions())

    permissoes = {
        'beeapi.view_mapa': request.user.has_perm('beeapi.view_mapa')
    }

    if not all(permissoes.values()):
        return HttpResponseForbidden('Voce nao tem permissao de visualizar mapas.')
    
    if request.user.is_superuser:
        mapas = Mapa.objects.all().order_by('nome')
    else:
        mapas = Mapa.objects.filter(grupos_mapas__grupo__in=request.user.groups.all()).distinct().order_by('nome')

    # Paginador
    pag = Paginator(mapas, 10)
    num_page = request.GET.get('page')
    page_obj = pag.get_page(num_page)

    total = len(mapas)

    total_ativo = len([j for j in mapas if j.status])
    total_desativado = len([j for j in mapas if not j.status])

    dados = {
        'mapas': mapas,
        'total': total,
        'page_obj': page_obj,
        'total_ativo': total_ativo,
        'total_desativado': total_desativado

    }
    if request.GET.get('page') and request.headers.get("HX-Request"):
        return render(request, "beeapi/edge_tabela.html", {"page_obj": page_obj})
    
    return render(request, template_name='beeapi/mapa_lista.html', context=dados)

def addMapa(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    #print('Permissoes do usuario:', request.user.get_all_permissions())

    permissoes = {
        'beeapi.add_mapa': request.user.has_perm('beeapi.add_mapa')
    }

    if not all(permissoes.values()):
        return HttpResponseForbidden('Voce nao tem permissao de adicionar mapas.')

    form = formAddMapa()

    if request.method == 'POST':
        form = formAddMapa(request.POST)
        if form.is_valid():
            mapa = form.save(commit=False)
            mapa.autor = request.user
            mapa.save()
            #return render(template_name='beeapi/mapa_sucesso.html', request=request)
            res = HttpResponse('')
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Mapa adicionado com sucesso!', 'resultado': 'ok', 'cor': 'success'}, 'atualiza': 'atualizando mapa'})
            return res
        else:
            res = render(request, template_name='beeapi/mapa_form.html', context={'form': form})
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Erro ao adicionar mapa!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
            return res
        
    return render(request, template_name='beeapi/mapa_form.html', context={'form': form})

def mapaEdit(request, id):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    permissoes = {
        'beeapi.view_mapa': request.user.has_perm('beeapi.view_mapa')
    }

    if not all(permissoes.values()):
        return HttpResponseForbidden('Voce nao tem permissao para editar mapas.')

    f = 'mapaEdit'

    mapa = get_object_or_404(Mapa, id=id)

    acao = request.POST.get('action')

    form = formAddMapa(instance=mapa)

    if request.method == 'POST' and acao == 'salvar':

        if not request.user.has_perm('beeapi.change_mapa'):
            return HttpResponseForbidden('Voce nao tem permissao pra editar o mapa.')

        form = formAddMapa(request.POST, instance=mapa)
        if form.is_valid():
            form.save()
            #return render(request=request, template_name='beeapi/mapa_sucesso.html', status=200)
            res = HttpResponse('')
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Mapa editado com sucesso!', 'resultado': 'ok', 'cor': 'success'}, 'atualiza': 'atualizando mapa'})
            return res
        else:
            res = render(request, template_name='beeapi/mapa_form.html', context={'form': form})
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Erro ao editar mapa!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
            return res
        
    elif request.method == 'POST' and acao == 'remover':

        if not request.user.has_perm('beeapi.delete_mapa'):
            return HttpResponseForbidden('Voce nao tem permissao pra remover o mapa.')

        form = formAddMapa(request.POST, instance=mapa)
        if Mapa.objects.count() > 1:
            mapa.delete()
            #return render(request=request, template_name='beeapi/mapa_sucesso.html', status=200)
            #res = HttpResponse('')
            res = render(request=request, template_name='beeapi/mapa_sucesso.html', status=200)
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Mapa removido com sucesso!', 'resultado': 'reload', 'cor': 'warning'}, 'atualiza': 'atualizando mapa'})
            return res
        else:
            dados = {
                'mapa': mapa,
                'form': form,
                'f': f
            }
            res = render(template_name='beeapi/mapa_form.html', context=dados, request=request, status=403)
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Você não pode remover todos os mapas!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
            return res
        
    if not tem_permissao(mapa=mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao para acessar o mapa_form nesse mapa.')
    
    dados = {
        'mapa': mapa,
        'form': form,
        'f': f
    }
    return render(template_name='beeapi/mapa_form.html', context=dados, request=request)

def listaNode(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    # Permissoes necessarias para essa view
    permissoes = {
        'beeapi.view_node': request.user.has_perm('beeapi.view_node')
    }

    if not all(permissoes.values()):
        return HttpResponseForbidden('Voce nao tem permissao para listar nodes.')

    mapaid = request.GET.get('mapaid')

    if not mapaid:
        return HttpResponseBadRequest('Mapaid nao informado.')

    mapa = get_object_or_404(Mapa, id=mapaid)

    #print('Permisao:', permissao)
    #print('Grupos do usuario:', list(request.user.groups.all().values()))

    #if not permissao:
    #    return HttpResponseForbidden()

    if not tem_permissao(mapa=mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao para listar nodes nesse mapa.')

    servidor = Servidor.objects.get(mapa=mapa.id)
    servidorid = servidor.id
    
    #print('Mapa Atual:', mapaid)
    nodes = Node.objects.filter(mapa=mapaid).order_by('nome').values()
    total = len(nodes)

    # Paginador
    pag = Paginator(nodes, 10)
    num_page = request.GET.get('page')
    page_obj = pag.get_page(num_page)

    # Analisando triggers dos nodes
    triggers = [i['indicador']['triggers'] for i in nodes if i['indicador']]
    triggers = [i for j in triggers for i in j]
    res_tgs = []
    res_tgs = async_to_sync(triggers_teste)(tgs=triggers, id=servidorid)
    triggers_dc = {}
    if res_tgs:
        triggers_dc = {i['triggerid']: i for i in res_tgs}

    # Status vem da API
    for i in nodes:
        i['mapa'] = Mapa.objects.get(id=i['mapa_id']).nome # Nome do mapa

        if isinstance(i['indicador'], (dict)):
            tgs = [triggers_dc.get(i) for i in i['indicador'].get('triggers') if i]
            status = valida_status(indicadores = tgs, modo=i['indicador']['modo']) # Tenho que consultar a api do zbx
            i['status'] = status
        else:
            i['status'] = 'erro'

    #print('Debug:', nodes)
    total_up = len([j for j in nodes if 'status' in j and j['status'] == 'up'])
    total_down = len([j for j in nodes if 'status' in j and j['status'] == 'down'])
    total_erro = len([j for j in nodes if 'status' in j and j['status'] == 'erro'])
    dados = {
        'nodes': nodes,
        'total': total,
        'total_up': total_up,
        'total_down': total_down,
        'total_erro': total_erro,
        'mapa': mapa,
        'page_obj': page_obj,
        #'permissao': permissao
    }

    if request.GET.get('page') and request.headers.get("HX-Request"):
        return render(request, "beeapi/node_tabela.html", {"page_obj": page_obj})

    return render(request=request, template_name='beeapi/node_lista.html', context=dados)

def addNode(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    # Permissoes necessarias para essa view
    permissoes = {
        'beeapi.add_node': request.user.has_perm('beeapi.add_node')
    }

    # Validando se o usuario tem as permissoes necessarias para criar um node
    if not all(permissoes.values()):
        return HttpResponseForbidden('Voce nao tem permissao de adicionar nodes.')

    f = 'addNode'

    form = formAddNode()

    if request.method == 'POST':
        form = formAddNode(request.POST)

        mapaid = request.POST.get('mapa')
        mapa = get_object_or_404(Mapa, id=mapaid)

        if not tem_permissao(mapa, request):
            return HttpResponseForbidden('Voce nao tem permissao para adicionar um node nesse mapa.')
        
        dados = {
                'form': form,
                'f': f,
                'mapa': mapa
            }

        if form.is_valid():
            form.save()
            #return render(template_name='beeapi/node_sucesso.html', request=request)
            res = HttpResponse('')
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Node adicionado com sucesso!', 'resultado': 'ok', 'cor': 'success'}, 'atualiza': 'atualizando mapa'})
            return res
        else: # Caso o form tenha campos invalidos
            res = render(template_name='beeapi/node_form.html', context=dados, request=request, status=403)
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Erro ao adicionar node!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
            return res

    # Se vier como GET vamos filtrar o mapaid com base no mapaid que vier
    mapaid = request.GET.get('mapaid')
    mapa = get_object_or_404(Mapa, id=mapaid)

    if not tem_permissao(mapa, request):
        return HttpResponseForbidden('Voce nao tem permissao para acessar o node_form nesse mapa.')

    #print (dir(form.fields['mapa']))
    form.fields['mapa'].initial = mapa
    form.fields['mapa'].queryset = Mapa.objects.filter(id=mapaid) # Filtrando mapa de acordo com o mapa selecionado e instanciando somente o mapa atual na lista

    dados = {
        'form': form,
        'f': f,
        'mapa': mapa
    }

    return render(template_name='beeapi/node_form.html', context=dados, request=request)

def nodeEdit(request, nodeid):

    #print('GET:', request.GET)
    #print('POST:', request.POST)
    #print('Nodeid:', nodeid)

    # Permissoes necessarias para essa view
    permissoes = {
        'view_node': request.user.has_perm('beeapi.view_node')
    }

    # Validando se o usuario tem as permissoes necessarias para editar um node
    if not all(permissoes.values()):
        return HttpResponseForbidden('Voce nao tem permissao para visualizar nodes.')

    f = 'nodeEdit'
    node = get_object_or_404(Node, nodeid=nodeid)

    mapa = Mapa.objects.get(id=node.mapa.id)
    servidor = Servidor.objects.get(mapa=mapa.id)
    servidorid = servidor.id

    # Validando se o usuario pode editar o mapa que esta solicitando
    if not tem_permissao(mapa=mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao de editar nodes desse mapa.')

    acao = request.POST.get('action')

    form = formAddNode(instance=node)
    form.fields['mapa'].initial = mapa
    form.fields['mapa'].queryset = Mapa.objects.filter(id=mapa.id)

    # Testando atualizacao direta
    ind = node.indicador

    its = []
    tgs = []
    modo = None

    # Quando for GET vamos tabelar os itens vinculados ao node
    if ind and isinstance(ind, (dict)):
        data_itens = ind['itens']
        data_triggers = ind['triggers']
        modo = ind['modo']

        if data_itens:
            its = async_to_sync(itens_teste)(its=data_itens, id=servidorid)
        if data_triggers:
            tgs = async_to_sync(triggers_teste)(tgs=data_triggers, id=servidorid)

        for j in its:
            # Aqui vamos formatar o valor com a sua unidade
            j['lastvalue'] = formata_uni(unidade=j['units'], valor=j['lastvalue'])
            # Aqui vamos tentar remover o .0 de numeros inteiros
            try:
                j['lastvalue'] = float(j['lastvalue'])
                if j['lastvalue'].is_integer():
                    j['lastvalue'] = str(j['lastvalue']).replace('.0', '')
            except:
                pass
        
        if its:
            its = {i['itemid']: i for i in its if its}.items()
        if tgs:
            tgs = {i['triggerid']: i for i in tgs if tgs}.items()

    if request.method == 'POST' and acao == 'salvar':

        if not request.user.has_perm('beeapi.change_node'):
            return HttpResponseForbidden('Voce nao tem permissao para editar nodes.')

        form = formAddNode(request.POST, instance=node)
        if form.is_valid():
            form.save()
            print('Node atualizado.')
            #res = render(template_name='beeapi/node_sucesso.html', request=request)
            res = HttpResponse('')
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Node editado com sucesso!', 'resultado': 'ok', 'cor': 'success'}, 'atualiza': 'atualizando mapa'})
            return res
        else:
            print('Erro ao atualizar node.')
            dados = {
                'form': form,
                'mapa': mapa,
                'f': f,
                'node': node,
                'itens': its,
                'triggers': tgs
            }
            res = render(template_name='beeapi/node_form.html', context=dados, request=request)
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Erro ao editar node!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
            return res
        
    elif request.method == 'POST' and acao == 'remover':

        if not request.user.has_perm('beeapi.delete_node'):
            return HttpResponseForbidden('Voce nao tem permissao para deletar nodes.')

        node.delete()
        #res = render(template_name='beeapi/node_sucesso.html', request=request)
        res = HttpResponse('')
        res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Node removido com sucesso!', 'resultado': 'ok', 'cor': 'warning'}, 'atualiza': 'atualizando mapa'})
        return res

    dados = {
        'node': node,
        'form': form,
        'f': f,
        'itens': its,
        'triggers': tgs,
        'mapa': mapa,
        'modo': modo
    }

    return render(template_name='beeapi/node_form.html', context=dados, request=request)

def listaEdge(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    permissoes = {
        'beeapi.view_edge': request.user.has_perm('beeapi.view_edge')
    }

    if not all(permissoes.values()):
        return HttpResponseForbidden('Voce nao tem permissao para visualizar edges.')

    mapaid = request.GET.get('mapaid')

    if not mapaid:
        return HttpResponseBadRequest('Mapaid nao informado.')

    mapa = get_object_or_404(Mapa, id=mapaid)
    servidor = Servidor.objects.get(mapa=mapa.id)
    servidorid = servidor.id

    if not tem_permissao(mapa=mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao para listar edges nesse mapa.')

    edges = Edge.objects.filter(mapa=mapa.id).order_by('nome').values()

    total = len(edges)

    # Paginador
    pag = Paginator(edges, 10)
    num_page = request.GET.get('page')
    page_obj = pag.get_page(num_page)

    # Analisando triggers dos nodes
    triggers = [i['indicador']['triggers'] for i in edges if i['indicador']]
    triggers = [i for j in triggers for i in j]
    res_tgs = []
    res_tgs = async_to_sync(triggers_teste)(tgs=triggers, id=servidorid)
    triggers_dc = {}
    if res_tgs:
        triggers_dc = {i['triggerid']: i for i in res_tgs}

    # Status vem da API
    for i in edges:
        i['mapa'] = Mapa.objects.get(id=i['mapa_id']).nome # Nome do mapa
        i['source'] = Node.objects.get(nodeid=i['source_id']).nome # Nome do node source
        i['target'] = Node.objects.get(nodeid=i['target_id']).nome # Nome do node target

        if isinstance(i['indicador'], (dict)):
            tgs = [triggers_dc.get(i) for i in i['indicador'].get('triggers') if i]
            status = valida_status(indicadores = tgs, modo=i['indicador']['modo']) # Tenho que consultar a api do zbx
            i['status'] = status
        else:
            i['status'] = 'erro'

    #print('Debug:', nodes)
    total_up = len([j for j in edges if 'status' in j and j['status'] == 'up'])
    total_down = len([j for j in edges if 'status' in j and j['status'] == 'down'])
    total_erro = len([j for j in edges if 'status' in j and j['status'] == 'erro'])

    dados = {
        'edges': edges,
        'total': total,
        'total_up': total_up,
        'total_down': total_down,
        'total_erro': total_erro,
        'mapa': mapa,
        'page_obj': page_obj
    }

    if request.GET.get('page') and request.headers.get("HX-Request"):
        return render(request, "beeapi/edge_tabela.html", {"page_obj": page_obj})

    return render(request=request, template_name='beeapi/edge_lista.html', context=dados)

def addEdge(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    # Permissoes necessarias para essa view
    permissoes = {
        'add_edge': request.user.has_perm('beeapi.add_edge')
    }

    # Validando se o usuario tem as permissoes necessarias para criar um edge
    if not all(permissoes.values()):
        return HttpResponseForbidden('Voce nao tem permissao para adicionar edges.')

    f = 'addEdge'

    form = formAddEdge()

    if request.method == 'POST':
        mapaid = request.POST.get('mapa')
        mapa = get_object_or_404(Mapa, id=mapaid)

        if not tem_permissao(mapa=mapa, request=request):
            return HttpResponseForbidden('Voce nao tem permissao para adicionar edges nesse mapa.')

        form = formAddEdge(request.POST)

        if form.is_valid():
            edge = form.save(commit=False)
            if not form.cleaned_data['nome']:
                edge.nome = f"{form.cleaned_data['source']}-com-{form.cleaned_data['target']}-bee-{str(secrets.token_hex(4))}"
            edge.save()
            #return render(template_name='beeapi/edge_sucesso.html', request=request)
            res = HttpResponse('')
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Edge adicionado com sucesso!', 'resultado': 'ok', 'cor': 'success'}, 'atualiza': 'atualizando mapa'})
            return res
        else:
            dados = {
                'f': f,
                'form': form
            }
            res = render(template_name='beeapi/edge_form.html', context=dados, request=request)
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Falha ao adicionar edge!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
            return res
        
    # Se vier como GET vamos filtrar o mapaid com base no mapaid que vier
    mapaid = request.GET.get('mapaid')
    mapa = get_object_or_404(Mapa, id=mapaid)

    # # Validando se o usuario pode editar o mapa que esta solicitando
    if not tem_permissao(mapa=mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao para acessar o form_edge nesse mapa.')
        
    form.fields['mapa'].initial = mapa
    form.fields['mapa'].queryset = Mapa.objects.filter(id=mapa.id)
    form.fields['source'].queryset = Node.objects.filter(mapa=mapa.id)
    form.fields['target'].queryset = Node.objects.filter(mapa=mapa.id)

    dados = {
        'form': form,
        'f': f,
        'mapa': mapa
    }

    return render(template_name='beeapi/edge_form.html', context=dados, request=request)

def edgeEdit(request, edgeid):
    
    #print('GET:', request.GET)
    #print('POST:', request.POST)

    # Permissoes necessarias para essa view
    permissoes = {
        'view_edge': request.user.has_perm('beeapi.view_edge')
    }

    # Validando se o usuario tem as permissoes necessarias para editar um edge
    if not all(permissoes.values()):
        return HttpResponseForbidden('Voce nao tem permissao para visualizar edges.')
    
    f = 'edgeEdit'

    edge = get_object_or_404(Edge, edgeid=edgeid)

    # No caso do edit eu ja recebo o elementoid, entao posso filtrar direto
    mapaid = edge.mapa.id
    mapa = Mapa.objects.get(id=mapaid)
    servidor = Servidor.objects.get(id=mapa.servidor.id)
    servidorid = servidor.id

    if not tem_permissao(mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao para acessar os edges desse mapa.')

    acao = request.POST.get('action')

    form = formAddEdge(instance=edge)

    # Testando atualizacao direta
    ind = edge.indicador

    its = []
    tgs = []
    modo = None

    if ind and isinstance(ind, (dict)):
        data_itens = ind['itens']
        data_triggers = ind['triggers']
        modo = ind['modo']

        if data_itens:
            its = async_to_sync(itens_teste)(its=data_itens, id=servidorid)
        
        if data_triggers:
            tgs = async_to_sync(triggers_teste)(tgs=data_triggers, id=servidorid)

        for j in its:
            j['lastvalue'] = formata_uni(unidade=j['units'], valor=j['lastvalue'])
            try:
                j['lastvalue'] = float(j['lastvalue'])
                if j['lastvalue'].is_integer():
                    j['lastvalue'] = str(j['lastvalue']).replace('.0', '')
            except:
                pass
        #print('Resultado:', its)
        if its:
            its = {i['itemid']: i for i in its if its}.items()
        if tgs:
            tgs = {i['triggerid']: i for i in tgs if tgs}.items()

    if request.method == 'POST' and acao == 'salvar':

        if not request.user.has_perm('beeapi.change_edge'):
            return HttpResponseForbidden('Voce nao tem permissao para editar edges.')

        form = formAddEdge(request.POST, instance=edge)
        if form.is_valid():
            edge = form.save(commit=False)
            if not form.cleaned_data['nome']:
                edge.nome = f"{form.cleaned_data['source']}-com-{form.cleaned_data['target']}-bee-{str(secrets.token_hex(4))}"
            edge.save()
            #return render(template_name='beeapi/edge_sucesso.html', request=request)
            res = HttpResponse('')
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Edge editado com sucesso!', 'resultado': 'ok', 'cor': 'success'}, 'atualiza': 'atualizando mapa'})
            return res
        else:
            dados = {
                'form': form,
                'mapa': mapa,
                'f': f,
                'edge': edge,
                'itens': its,
                'triggers': tgs
            }
            res = render(template_name='beeapi/edge_form.html', request=request, context=dados)
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Falha ao editar edge!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
            return res
        
    elif request.method == 'POST' and acao == 'remover':

        if not request.user.has_perm('beeapi.delete_edge'):
            return HttpResponseForbidden('Voce nao tem permissao para deletar edges.')

        edge.delete()
        #return render(template_name='beeapi/edge_sucesso.html', request=request)
        res = HttpResponse('')
        res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Edge removido com sucesso!', 'resultado': 'ok', 'cor': 'warning'}, 'atualiza': 'atualizando mapa'})
        return res
    
    form.fields['mapa'].initial = mapa
    form.fields['mapa'].queryset = Mapa.objects.filter(id=mapa.id)
    form.fields['source'].queryset = Node.objects.filter(mapa=mapa.id)
    form.fields['target'].queryset = Node.objects.filter(mapa=mapa.id)

    dados = {
        'edge': edge,
        'form': form,
        'f': f,
        'itens': its,
        'triggers': tgs,
        'mapa': mapa,
        'modo': modo
    }

    return render(template_name='beeapi/edge_form.html', context=dados, request=request)

def consulta_grupos(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    if request.method != "GET":
        return JsonResponse({"Erro": "Metodo invalido"}, status=405)

    elemento = request.GET.get('elemento')
    elementoid = request.GET.get('elementoid')

    if not all([elemento, elementoid]):
        return JsonResponse({'Erro': 'Paramentros insuficientes.'}, status=400)

    if elemento == 'node':
        ele = get_object_or_404(Node, nodeid=elementoid)
    elif elemento == 'edge':
        ele = get_object_or_404(Edge, edgeid=elementoid)

    mapa = Mapa.objects.get(id=ele.mapa.id)
    servidor = Servidor.objects.get(mapa=mapa.id)
    servidorid = servidor.id

    if not tem_permissao(mapa=mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao para integrar grupos nesse mapa.')

    dados = {}

    q = request.POST.get('procura', '')
    #res = requests.get(f'{host_api}/grupos')

    res = async_to_sync(grupos_teste)(id=servidorid)
    #print('Resultado:', res.text)
    #res = json.loads(res.text)

    #print('Busca por grupos:', q)

    grupos = []

    for i in res:
        if q.lower() in i['nome'].lower():
            grupos.append(i)

    #print(grupos)

    dados = {
        'grupos': grupos,
        'elemento': elemento,
        'elementoid': elementoid
    }

    return render(template_name='beeapi/integracao_grupos.html', context=dados, request=request)

def consulta_hosts(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    if request.method != "GET":
        return JsonResponse({"Erro": "Metodo invalido"}, status=405)

    elemento = request.GET.get('elemento')
    elementoid = request.GET.get('elementoid')

    if not all([elemento, elementoid]):
        return JsonResponse({'Erro': 'Paramentros insuficientes.'}, status=400)

    if elemento == 'node':
        ele = get_object_or_404(Node, nodeid=elementoid)
    elif elemento == 'edge':
        ele = get_object_or_404(Edge, edgeid=elementoid)

    mapa = Mapa.objects.get(id=ele.mapa.id)
    servidor = Servidor.objects.get(mapa=mapa.id)
    servidorid = servidor.id

    if not tem_permissao(mapa=mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao para integrar hosts nesse mapa.')

    q = request.GET.get('grupos', '')

    #print('Os hosts desse grupo serao buscados:', q)

    lista_grupos = []

    lista_grupos.append(q)

    data = {
        'grupos': lista_grupos
    }

    #res = requests.post(f'{host_api}/hosts', json=data)
    #print(res.json())

    res = async_to_sync(hosts_teste)(grupos=data, id=servidorid)
    #res = json.loads(res.text)

    hosts = []

    for i in res:
        hosts.append(i)

    #print('Hosts:', hosts)

    dados = {
        'hosts': hosts,
        'elemento': elemento,
        'elementoid': elementoid
    }

    return render(template_name='beeapi/integracao_hosts.html', context=dados, request=request)

def consulta_itens_triggers(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    if request.method != "GET":
        return JsonResponse({"Erro": "Metodo invalido"}, status=405)

    elemento = request.GET.get('elemento')
    elementoid = request.GET.get('elementoid')

    if not all([elemento, elementoid]):
        return JsonResponse({'Erro': 'Paramentros insuficientes.'}, status=400)

    if elemento == 'node':
        ele = get_object_or_404(Node, nodeid=elementoid)
    elif elemento == 'edge':
        ele = get_object_or_404(Edge, edgeid=elementoid)

    mapa = Mapa.objects.get(id=ele.mapa.id)
    servidor = Servidor.objects.get(mapa=mapa.id)
    servidorid = servidor.id

    if not tem_permissao(mapa=mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao para integrar itens e triggers nesse mapa.')

    hostid = request.GET.get('hosts', '')

    #print('Hostids:', q)

    lista_hostsids = []
    lista_hostsids.append(hostid)

    #res = requests.get(f'{host_api}/itens?hostid={q}')
    #res = requests.post(f'{host_api}/itens', json=data)
    #its = res.json()
    #res2 = requests.get(f'{host_api}/triggers?hostid={q}')
    #tgs = res2.json()

    #print('Its:', res.json())
    #print('Tgs:', res2.json())

    its = async_to_sync(itens_teste)(hostid=hostid, id=servidorid)
    #its = json.loads(res_its.text)

    tgs = async_to_sync(triggers_teste)(hostid=hostid, id=servidorid)
    #tgs = json.loads(res_tgs.text)

    dados = {
        'itens': its,
        'triggers': tgs,
        'elemento': elemento,
        'elementoid': elementoid
    }

    #print(dados)

    return render(template_name='beeapi/integracao_itens_triggers.html', context=dados, request=request)

def consulta_itens(request):

    #print('POST:', request.POST)
    #print('GET:', request.GET)

    # Nesse caso como post, pois preciso usar outros parametros do form (hostid)
    if request.method != "POST":
        return JsonResponse({"Erro": "Metodo invalido"}, status=405)

    elemento = request.POST.get('elemento')
    elementoid = request.POST.get('elementoid')

    if not all([elemento, elementoid]):
        return JsonResponse({'Erro': 'Paramentros insuficientes.'}, status=400)

    if elemento == 'node':
        ele = get_object_or_404(Node, nodeid=elementoid)
    elif elemento == 'edge':
        ele = get_object_or_404(Edge, edgeid=elementoid)

    mapa = Mapa.objects.get(id=ele.mapa.id)
    servidor = Servidor.objects.get(mapa=mapa.id)
    servidorid = servidor.id

    if not tem_permissao(mapa=mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao para consultar itens nesse mapa.')

    q = request.POST.get('filtrar_itens', '')
    hostid = request.POST.get('hosts')

    #print('Itens para filtrar:', q)
    #print('Hosts para filtrar:', hostid)

    #res = requests.get(f'{host_api}/itens?hostid={hostid}')
    #res = requests.post(f'{host_api}/itens', json=data)
    #its = res.json()

    its = async_to_sync(itens_teste)(hostid=hostid, id=servidorid)
    #its = json.loads(res_its.text)

    lista_filtrada = []

    for i in its:
        if q.lower() in i['nome'].lower():
            lista_filtrada.append(i)

    #print('Its:', lista_filtrada)

    dados = {
        'itens': lista_filtrada,
        'elemento': elemento,
        'elementoid': elementoid
    }

    return render(template_name='beeapi/integracao_itens.html', context=dados, request=request)

def consulta_triggers(request):

    #print('POST:', request.POST)
    #print('GET:', request.GET)

    # Nesse caso como post, pois preciso usar outros parametros do form (hostid)
    if request.method != "POST":
        return JsonResponse({"Erro": "Metodo invalido"}, status=405)

    elemento = request.POST.get('elemento')
    elementoid = request.POST.get('elementoid')

    if not all([elemento, elementoid]):
        return JsonResponse({'Erro': 'Paramentros insuficientes.'}, status=400)

    if elemento == 'node':
        ele = get_object_or_404(Node, nodeid=elementoid)
    elif elemento == 'edge':
        ele = get_object_or_404(Edge, edgeid=elementoid)

    mapa = Mapa.objects.get(id=ele.mapa.id)
    servidor = Servidor.objects.get(mapa=mapa.id)
    servidorid = servidor.id

    if not tem_permissao(mapa=mapa, request=request):
        return HttpResponseForbidden('Voce nao tem permissao para consultar triggers nesse mapa.')

    q = request.POST.get('filtrar_triggers', '')
    hostid = request.POST.get('hosts')

    #print('Triggers para filtrar:', q)

    #res = requests.get(f'{host_api}/triggers?hostid={hostid}')
    #res = requests.post(f'{host_api}/itens', json=data)
    #tgs = res.json()

    tgs = async_to_sync(triggers_teste)(hostid=hostid, id=servidorid)
    #tgs = json.loads(res_tgs.text)

    #print('Debug:', tgs)

    lista_filtrada = []

    for i in tgs:
        if q.lower() in i['nome'].lower():
            lista_filtrada.append(i)

    #print('Tgs:', lista_filtrada)

    dados = {
        'triggers': lista_filtrada,
        'elemento': elemento,
        'elementoid': elementoid
    }

    return render(template_name='beeapi/integracao_triggers.html', context=dados, request=request)

def integracao_inicio(request):

    #print('POST:', request.POST)
    #print('GET:', request.GET)

    if request.method != "GET":
        return JsonResponse({"Erro": "Metodo invalido"}, status=405)

    elemento = request.GET.get('elemento')
    elementoid = request.GET.get('elementoid')
    
    #print('ElementoID:', elementoid)
    #print('Elemento:', elemento)

    if not all([elemento, elementoid]):
        return JsonResponse({'Erro': 'Paramentros insuficientes.'}, status=400)

    if elemento == 'node':
        #node = get_object_or_404(Node, nodeid=elementoid)
        dados = {
            'elemento': elemento,
            'elementoid': elementoid
        }
    elif elemento == 'edge':
        #edge = get_object_or_404(Edge, edgeid=elementoid)
        dados = {
            'elemento': elemento,
            'elementoid': elementoid
        }

    return render(template_name='beeapi/integracao_form.html', context=dados, request=request)

def integracao_revisao(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    if request.method != "POST":
        return JsonResponse({"Erro": "Metodo invalido"}, status=405)

    elemento = request.GET.get('elemento')
    elementoid = request.GET.get('elementoid')

    #print('Elemento:', elemento)
    #print('ElementoID:', elementoid)

    if not all([elemento, elementoid]):
        return JsonResponse({'Erro': 'Paramentros insuficientes.'}, status=400)

    dados = {}

    if elemento == 'node':
        node = get_object_or_404(Node, nodeid=elementoid)
        mapa = Mapa.objects.get(id=node.mapa_id)

        if not tem_permissao(mapa, request):
            return HttpResponseForbidden('Voce nao tem permissao para integrar nodes desse mapa.')

        dados = {
            'elemento': elemento,
            'id': node.nodeid
        }
    elif elemento == 'edge':
        edge = get_object_or_404(Edge, edgeid=elementoid)
        mapa = Mapa.objects.get(id=edge.mapa_id)

        if not tem_permissao(mapa, request):
            return HttpResponseForbidden('Voce nao tem permissao para integrar edges desse mapa.')

        dados = {
            'elemento': elemento,
            'id': edge.edgeid
        }

    if request.method == 'POST':

        indicadores = {
            #'elementoid': elementoid,
            'grupos': request.POST.get('grupos', ''),
            'hosts': request.POST.get('hosts', ''),
            'itens': request.POST.getlist('itens', []),
            'triggers': request.POST.getlist('triggers', []),
            'modo': request.POST.get('modo', '')
        }

        # itens e triggers passam a ser opcionais
        validador = {
            #'elementoid': elementoid,
            'grupos': request.POST.get('grupos', ''),
            'hosts': request.POST.get('hosts', ''),
            'modo': request.POST.get('modo', '')
        }

        # So passa se todos os indicadores tiverem valores
        if all(validador.values()):

            if elemento == 'node':
                #node.indicador = indicadores

                if not request.user.has_perm('beeapi.change_node'):
                    return HttpResponseForbidden('Voce nao tem permissao para editar nodes.')

                if node.indicador:
                    [node.indicador['itens'].append(i) for i in indicadores['itens'] if i not in node.indicador['itens']]
                    [node.indicador['triggers'].append(i) for i in indicadores['triggers'] if i not in node.indicador['triggers']]
                    node.save()
                else:
                    node.indicador = indicadores
                    node.save()

                print('Node atualizado.')

            elif elemento == 'edge':
                #edge.indicador = indicadores

                if not request.user.has_perm('beeapi.change_edge'):
                    return HttpResponseForbidden('Voce nao tem permissao para editar edges.')

                if edge.indicador:
                    [edge.indicador['itens'].append(i) for i in indicadores['itens'] if i not in edge.indicador['itens']]
                    [edge.indicador['triggers'].append(i) for i in indicadores['triggers'] if i not in edge.indicador['triggers']]
                    edge.save()
                else:
                    edge.indicador = indicadores
                    edge.save()

                print('Edge atualizado.')

            # Html com mensagem de retorno sucesso ou erro
            #return render(template_name='beeapi/integracao_sucesso.html', context=dados, request=request)
            res = HttpResponse('')
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Integração realizada com sucesso!', 'resultado': 'ok', 'cor': 'success'}, 'atualiza': 'atualizando mapa'})
            return res
        else:
            res = HttpResponse('')
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Falha ao realizar integração!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
            return res

    return render(template_name='beeapi/integracao_form.html', context=dados, request=request)

def edita_itens_triggers(request):
    
    #print('GET:', request.GET)
    #print('POST:', request.POST)

    elemento = request.GET.get('elemento')
    elementoid = request.GET.get('elementoid')

    if elemento == 'node':
        ele = get_object_or_404(Node, nodeid=elementoid)
        mapa = Mapa.objects.get(id=ele.mapa_id)

        if not tem_permissao(mapa, request):
            return HttpResponseForbidden('Voce nao tem permissao para editar itens e triggers para esse node nesse mapa.')

    elif elemento == 'edge':
        ele = get_object_or_404(Edge, edgeid=elementoid)
        mapa = Mapa.objects.get(id=ele.mapa_id)

        if not tem_permissao(mapa, request):
            return HttpResponseForbidden('Voce nao tem permissao para editar itens e triggers para esse edge nesse mapa.')

    else:
        print('Elemento invalido')
        return JsonResponse({'Erro': 'Elemento invalido'})

    itemid = request.GET.get('itemid')
    triggerid = request.GET.get('triggerid')

    if elemento == 'node':
        if not request.user.has_perm('beeapi.change_node'):
            return HttpResponseForbidden('Voce nao tem permissao para editar nodes.')
    elif elemento == 'edge':
        if not request.user.has_perm('beeapi.change_edge'):
            return HttpResponseForbidden('Voce nao tem permissao para editar edges.')

    if ele.indicador and 'itens' in ele.indicador and itemid in ele.indicador['itens']:
        ele.indicador['itens'].remove(itemid)
        ele.save()

        #print(node.indicador)

        res = HttpResponse('')
        res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Item removido com sucesso!', 'resultado': 'ok', 'cor': 'warning'}, 'atualiza': 'atualizando mapa'})
        return res

    elif ele.indicador and 'triggers' in ele.indicador and triggerid in ele.indicador['triggers']:
        ele.indicador['triggers'].remove(triggerid)
        ele.save()

        #print(node.indicador)

        res = HttpResponse('')
        res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Trigger removida com sucesso!', 'resultado': 'ok', 'cor': 'warning'}, 'atualiza': 'atualizando mapa'})
        return res
    else:
        res = HttpResponse('')
        res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Falha ao remover!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
        return res

def modo(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    mapaid = request.GET.get('mapaid')
    elementoid = request.GET.get('elementoid')
    elemento = request.GET.get('elemento')

    dados = {
        'mapaid': mapaid,
        'elementoid': elementoid,
        'elemento': elemento
    }

    if request.method == 'POST':
        op = request.POST.get('op')
        elementoid = request.POST.get('elementoid')
        elemento = request.POST.get('elemento')

        if elemento == 'node':
            ele = get_object_or_404(Node, nodeid=elementoid)
            mapa = Mapa.objects.get(id=ele.mapa_id)

            if not tem_permissao(mapa, request):
                return HttpResponseForbidden('Voce nao tem permissao para editar o modo no node nesse mapa.')

            ele.indicador['modo'] = op
            ele.save()
            print('Node:', ele.indicador)

        elif elemento == 'edge':
            ele = get_object_or_404(Edge, edgeid=elementoid)
            mapa = Mapa.objects.get(id=ele.mapa_id)

            if not tem_permissao(mapa, request):
                return HttpResponseForbidden('Voce nao tem permissao para editar o modo no edge nesse mapa.')
            
            ele.indicador['modo'] = op
            ele.save()
            print('Edge:', ele.indicador)
        else:
            print('Opcao invalida!')
            res = HttpResponse('')
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Erro ao editar modo!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
            return res

        res = HttpResponse('')
        res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Modo editado!', 'resultado': 'ok', 'cor': 'success'}, 'atualiza': 'atualizando mapa'})
        return res

    return render(template_name='beeapi/modo_edit.html', request=request, context=dados)

# Funcoes gerais
def salvar_posicao(request):
    if request.method != "POST":
        return JsonResponse({"error": "Metodo invalido"}, status=405)

    data = json.loads(request.body)

    #print('Dados do body:', data)

    posicao = {
        'nodeid': data["id"],
        'x': data["x"],
        'y': data["y"]
    }

    if all(posicao.values()):

        # Validacao por grupo de usuario
        node = get_object_or_404(Node, nodeid=posicao['nodeid'])
        mapa = get_object_or_404(Mapa, id=node.mapa_id)

        if not tem_permissao(mapa, request):
            return HttpResponseForbidden('Voce nao tem permissao para acessar esse mapa.')

        if not request.user.has_perm('beeapi.change_mapa'):
            return HttpResponseForbidden('Voce nao tem permissao para editar esse mapa')

        Node.objects.filter(nodeid=posicao['nodeid']).update(x=posicao['x'], y=posicao['y'])
        return JsonResponse({"ok": 'Posicao salva!'}, status=200)
    else:
        return JsonResponse({"erro": 'Falha ao salvar posicao!'}, status=400)

def valida_status(indicadores, modo='any'):
    # Com a opcao any se qualquer item ficar down o status vai ser down
    #print('Indicadores:', indicadores)
    #print('Modo:', modo)
    
    #indicadores = json.loads(indicadores.text)

    if indicadores and modo == 'any':
        status_geral = "down" if any(v.get('status') == "down" for v in indicadores if isinstance(v, (dict))) else "up"
        return status_geral
    
    # Com a opcao all o status so vai ficar down se todos estiverem down
    elif indicadores and modo == 'all':
        status_geral = "down" if all(v.get('status') == "down" for v in indicadores if isinstance(v, (dict))) else "up"
        return status_geral
    else:
        #print('Modo invalido!')
        return 'erro'
    
def formata_uni(valor, unidade):
    try:
        return humanize.metric(valor, unidade)
    except Exception as e:
        print(f'Erro ao processar valor: {valor}', e)
        return valor

# Funcao para formatar o label
PATTERN = re.compile(r"\{\{(\d+)\}\}\s*\{\{(\w+)\}\}(?:\s*\{\{(.*?)\}\})?")

def render_label(template, indicadores):

    #print('Indicadores:', indicadores)
    #print('Template:', template)

    # Fazendo alguns replaces...

    if not template:
        if indicadores:
            label_default = ''
            for c,i in enumerate(indicadores): #c contador e i o valor
                label_default += f"Item{c}: {formata_uni(unidade=i['units'], valor=i['lastvalue'])}\n"
            return label_default
        else:
            #print('Elemento sem indicadores')
            return 'Crie as suas labels aqui'

    mapa = {i['itemid']: i for i in indicadores}

    def repl(m):
        chave, campo, unidade = m.groups()

        valor = mapa.get(chave, {}).get(campo, "")

        if unidade:
            #return f"{valor} {unidade}"
            return formata_uni(valor, unidade)
        return str(valor)
    
    #print('Label renderizada:', PATTERN.sub(repl, template))

    return PATTERN.sub(repl, template)

def formata_number(value):
    try:
        num = float(value)
        return int(num) if num.is_integer() else round(num, 2)
    except:
        return value
    
########### API Zabbix ##########

async def grupos_teste(id):
    # Lista de todos os grupos de um servidor especifico

    chave = 'grupos_cache'

    if cache.get(chave):
        return cache.get(chave)

    servidor = await sync_to_async(Servidor.objects.get)(id=id)
    url = servidor.url

    headers = {
        'Content-Type': 'application/json-rpc',
        'Authorization': f'Bearer {servidor.token}'
    }

    data = {
        "jsonrpc": "2.0",
        "method": "hostgroup.get",
        "params": {
            "output": ['groupid', 'name'],
            "sortfield": ['name'],
            "sortorder": 'ASC'
            },
        "id": 1
    }

    try:
        #res = requests.post(url=url, headers=headers, json=data)
        async with httpx.AsyncClient(verify=False) as cli:
            res = await cli.post(url=url, headers=headers, json=data)
    except:
        print('--> Erro ao conectar na API.')
        return None
    
    if res.status_code != 200:
        print('--> Api nao respondeu 200/ok.')
        return None

    #print(res.status_code)
    #print(json.dumps(res.json(), indent=3))

    dados = []

    try:
        res_js = res.json()['result']
    except:
        print('Erro ao processar json (grupos_teste)')
        return None

    for i in res_js:

        dc = {
            'groupid': i['groupid'],
            'nome': i['name']
        }

        dados.append(dc)

    cache.set(chave, dados, timeout=10)

    #print(json.dumps(dados, indent=3))

    return dados

async def hosts_teste(grupos, id):
    # Lista de hosts de um grupo passado assim {'grupos': ['10']}

    chave = f'hosts_cache_{grupos}'

    if cache.get(chave):
        return cache.get(chave)

    #print('Lista de grupos', grupos)
    grupos = grupos.get('grupos')

    servidor = await sync_to_async(Servidor.objects.get)(id=id)
    url = servidor.url

    headers = {
        'Content-Type': 'application/json-rpc',
        'Authorization': f'Bearer {servidor.token}'
    }

    data = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ['hostid', 'host'],
            "groupids": grupos,
            "filter": {'status': 0},
            "sortfield": ['host'],
            "sortorder": 'ASC'
            },
        "id": 1
    }

    #res = requests.post(url=url, headers=headers, json=data)

    try:
        async with httpx.AsyncClient(verify=False) as cli:
            res = await cli.post(url=url, headers=headers, json=data)
    except:
        print('--> Erro ao conectar na API.')
        return None
    
    if res.status_code != 200:
        print('--> Api nao respondeu 200/ok.')
        return None

    #print(res.status_code)
    #print(json.dumps(res.json(), indent=3))

    dados = []

    try:
        res_js = res.json()['result']
    except:
        print('Erro ao processar json (grupos_teste)')
        return None

    for i in res_js:

        dc = {
            'hostid': i['hostid'],
            'nome': i['host']
        }

        dados.append(dc)

    cache.set(chave, dados, timeout=10)

    #print(json.dumps(lista_final, indent=3))

    return dados

async def itens_teste(hostid=None, its=None, id=None):

    # Id do host: (hostid): 123
    # Lista de itens (its): ['123', '456']

    if hostid:
        chave = f'itens_hostid_cache_{hostid}'
    elif its:
        chave = f'itens_its_cache_{its}'
    else:
        print('Parametros invalidos, use hostid ou its')
        return None

    if cache.get(chave):
        return cache.get(chave)

    servidor = await sync_to_async(Servidor.objects.get)(id=id)
    url = servidor.url

    headers = {
        'Content-Type': 'application/json-rpc',
        'Authorization': f'Bearer {servidor.token}'
    }

    if hostid:
        data = {
            "jsonrpc": "2.0", "method": "item.get",
            "params": {"output": ['itemid', 'name', 'lastclock', 'lastvalue', 'prevvalue', 'units'],"hostids": [hostid],'selectHosts': ['hostid', 'host'],
            "filter": {'status': 0},
            "sortfield": ['name'],
            "sortorder": 'ASC',
            },
            "id": 1
            }
    elif its:
        data = {
            "jsonrpc": "2.0", "method": "item.get",
            "params": {"output": ['itemid', 'name', 'lastclock', 'lastvalue', 'prevvalue', 'units'],"itemids": its, 'selectHosts': ['hostid', 'host'],
            "sortfield": ['name'],
            "sortorder": 'ASC',
            },
            "id": 1
        }
    else:
        print('Opcao invalida')
        return None

    try:
        async with httpx.AsyncClient(verify=False) as cli:
            res = await cli.post(url=url, headers=headers, json=data)
    except:
        print('--> Erro ao conectar na API.')
        return None
    
    if res.status_code != 200:
        print('--> Api nao respondeu 200/ok.')
        return None

    #print(res.status_code)
    #print(json.dumps(res.json()['result'], indent=3))

    dados = []

    try:
        res_js = res.json()['result']
    except:
        print('Erro ao consultar json (itens_teste).')
        return None

    for i in res_js:
        dc = {
            'itemid': i['itemid'],
            'nome': i['name'],
            'hostid': i['hosts'][0]['hostid'],
            'host': i['hosts'][0]['host'],
            'lastclock': i['lastclock'],
            'lastclock_dt': dt.fromtimestamp(int(i['lastclock'])).isoformat(),
            'lastvalue': formata_number(i['lastvalue']),
            'prevvalue': formata_number(i['prevvalue']),
            'units': i['units']
        }

        dados.append(dc)
    
    cache.set(chave, dados, timeout=10)

    #print(json.dumps(dados, indent=3))

    return dados

async def triggers_teste(hostid=None, tgs=None, id=None):

    #print('Lista de hosts:', hostid)

    # Id do host: (hostid): 123
    # Lista de itens (its): ['123', '456']

    if hostid:
        chave = f'triggers_hostid_cache_{hostid}'
    elif tgs:
        chave = f'triggers_tgs_cache_{tgs}'
    else:
        print('Parametros invalidos, use hostid ou tgs')
        return None

    if cache.get(chave):
        return cache.get(chave)

    servidor = await sync_to_async(Servidor.objects.get)(id=id)
    url = servidor.url

    headers = {
        'Content-Type': 'application/json-rpc',
        'Authorization': f'Bearer {servidor.token}'
    }

    if hostid:

        data = {
            "jsonrpc": "2.0", "method": "trigger.get",
            "params": {"output": ['triggerid', 'description', 'value', 'lastchange', 'priority', 'opdata'], "hostids": [hostid], "selectHosts": ['hostid', 'host'], "monitored": True, "skipDependent": True, 'active': True,
            "sortfield": ['description'],
            "sortorder": 'ASC',
            },
            "id": 1
        }
    else:
        data = {
            "jsonrpc": "2.0","method": "trigger.get",
            "params": {"triggerids": tgs, "output": ['triggerid', 'description', 'value', 'lastchange', 'priority', 'opdata'], "selectHosts": ['hostid', 'host'], "monitored": True, "skipDependent": True, 'active': True,
            "sortfield": ['description'],
            "sortorder": 'ASC',
            },
            "id": 1
        }

    #res = requests.post(url=url, headers=headers, json=data)

    try:
        async with httpx.AsyncClient(verify=False) as cli:
            res = await cli.post(url=url, headers=headers, json=data)
    except:
        print('--> Erro ao conectar na API.')
        return None
    
    if res.status_code != 200:
        print('--> Api nao respondeu 200/ok.')
        return None

    #print(res.status_code)
    #print(json.dumps(res.json(), indent=3))

    dados = []

    try:
        res_js = res.json()['result']
    except:
        print('Erro ao consultar json (triggers_teste).')
        return None

    for i in res_js:

        status = i['value']
        if str(status) == '0':
            status = 'up'
        elif str(status) == '1':
            status = 'down'
        else:
            status = 'erro'

        dc = {
            'triggerid': i['triggerid'],
            'nome': i['description'],
            'hostid': i['hosts'][0]['hostid'],
            'host': i['hosts'][0]['host'],
            'status': status, # 0 ok 1 problema
            'lastchange': i['lastchange'],
            'lastchange_dt': dt.fromtimestamp(int(i['lastchange'])).isoformat(),
            'priority': i['priority'],
            'opdata': i['opdata']
        }
        dados.append(dc)

    cache.set(chave, dados, timeout=10)

    #print(json.dumps(dados, indent=3))

    return dados

async def historico_teste(its=None, id=None, inicio=None, fim=None):

    lista_de_itens = its

    if not its:
        print('Erro: Lista de itens vazia.')
        return JsonResponse({'Erro': 'Lista de itens vazia.'}, status=400)
    
    servidor = await sync_to_async(Servidor.objects.get)(id=id)
    url = servidor.url

    headers = {
        'Content-Type': 'application/json-rpc',
        'Authorization': f'Bearer {servidor.token}'
    }

    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": ['itemid', 'name', 'value_type', 'units'],
            "itemids": lista_de_itens
        },
        "id": 1
    }

    # Primeiro precisamos consultar qual o tipo de valor de cada item
    try:
        async with httpx.AsyncClient(verify=False) as cli:
            res = await cli.post(url=url, headers=headers, json=data)
    except:
        print('--> Erro ao conectar na API.')
        return None
    
    if res.status_code != 200:
        print('--> Api nao respondeu 200/ok.')
        return None

    #print(res.json())

    try:
        itens = res.json()['result']
    except:
        print('Erro ao processar itens (historico_teste).')
        return None

    lista_historico = []

    for i in itens:

        data = {
            "jsonrpc": "2.0",
            "method": "history.get",
            "params": {
                "output": "extend",
                "history": i.get('value_type'),
                "itemids": i.get('itemid'),
                "sortfield": "clock",
                "sortorder": "DESC",
                "time_from": inicio,
                "time_till": fim,
                "limit": 10 # Limitando somente para os ultimos 10
            },
            "id": 1
        }

        # Agora consultamos o historico de cada um dos items
        try:
            async with httpx.AsyncClient(verify=False) as cli:
                res = await cli.post(url=url, headers=headers, json=data)
        except:
            print('--> Erro ao conectar na API.')
            return None
        
        if res.status_code != 200:
            print('--> Api nao respondeu 200/ok.')
            return None

        data = {}

        try:
            his = res.json()['result']
        except:
            print('Erro ao processar historico. (historico_teste)')
            return None

        #datetime.fromtimestamp(int(i.get('clock'))).strftime('%d-%m %H:%M')

        dc = {
            'label': i.get('name'),
            'units': i.get('units'),
            'data': [{'x': dt.fromtimestamp(int(i.get('clock'))).isoformat(), 'y': i.get('value')} for i in his]
        }

        lista_historico.append(dc)
    
    return lista_historico

def retorna_grafico(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    itemid = request.GET.get('itemid')

    dados = {
        'itemid' : itemid
    }

    return render(template_name='beeapi/grafico.html', context=dados, request=request)

def retorna_historico(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    mapaid = request.GET.get('mapaid')
    servidor = Servidor.objects.get(mapa=mapaid)
    servidorid = servidor.id
    mapa = get_object_or_404(Mapa, id=mapaid)

    if not tem_permissao(mapa, request):
        return HttpResponseForbidden('Voce nao tem permissao para consultar o historico de itens nesse mapa.')

    itemid = request.GET.get('itemid')
    its = []
    its.append(itemid)

    uma_hora = timedelta(hours=1)
    inicio = dt.now() - uma_hora
    fim = dt.now()

    #print('Horario inicial:', inicio)
    #print('Horario final:', fim)

    inicio_ts = int(dt.timestamp(inicio))
    fim_ts = int(dt.timestamp(fim))

    #print('Horario inicial ts:', inicio_ts)
    #print('Horario final ts:', fim_ts)

    historico = async_to_sync(historico_teste)(its=its, id=servidorid, inicio=inicio_ts, fim=fim_ts)

    #print('Historico:', historico)

    dados = {
        'historico': historico
    }

    return JsonResponse(dados, safe=False)

def mapaExport(request, mapaid):
    
    #print('GET:', request.GET)
    #print('POST:', request.POST)

    #mapaid = request.GET.get('mapaid')

    mapa = get_object_or_404(Mapa, id=mapaid)

    if not tem_permissao(mapa, request):
        return HttpResponseForbidden('Voce nao tem permissao para exportar esse mapa.')

    nodes = Node.objects.filter(mapa=mapa).values('nome', 'descricao', 'label_template', 'x', 'y', 'icone', 'classe', 'indicador')
    edges = Edge.objects.filter(mapa=mapa).values('nome', 'descricao', 'label_template', 'source__nome', 'target__nome', 'indicador')

    dados = {}
    dados['nodes'] = list(nodes)
    dados['edges'] = list(edges)

    #print('Dados exportado:', dados)

    res = HttpResponse(
        json.dumps(dados, indent=3), content_type='application/json'
    )
    
    res['Content-Disposition'] = f"attachment; filename=beedude-{mapa.nome}.json"
    return res

def mapaImport(request):

    #print('GET:', request.GET)
    #print('POST:', request.POST)

    # Permissoes necessarias para criar/editar mapa via import
    permissoes = {
        'beeapi.add_mapa': request.user.has_perm('beeapi.add_mapa'),
        'beeapi.change_mapa': request.user.has_perm('beeapi.change_mapa')
    }

    if not all(permissoes.values()):
        return HttpResponseForbidden('Voce nao tem permissao para adicionar/editar mapas.')

    servidores = Servidor.objects.all()

    dados = {
        'servidores': servidores
    }

    if request.method == 'POST' and request.FILES.get('arquivo'):
        arquivo = request.FILES['arquivo']

        mapa_nome = request.POST.get('mapa_nome')
        servidor_id = request.POST.get('servidor')

        servidor = get_object_or_404(Servidor, id=servidor_id)

        validador = {
            'arquivo': arquivo,
            'mapa_nome': mapa_nome,
            'servidor_id': servidor_id
        }

        if not all(validador.values()):
            res = HttpResponse('')
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Erro ao importar mapa!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
            return res

        try:
            js = json.load(arquivo)
            if isinstance(js, (dict)):
                #print(js)

                nodes_para_add = []
                edges_para_add = []

                # Criando novo mapa | O update or create sempre retorna uma tupla com o objeto e o resultado, se criou true se atualizou false
                mapa_obj = Mapa.objects.update_or_create(nome=mapa_nome, servidor=servidor, autor=request.user)

                #print('Resultado:', mapa_obj)

                op = {
                    'mapa': mapa_obj[0],
                    'resultado': mapa_obj[1]
                }

                mapa = op.get('mapa')

                # Importando nodes
                for n in js.get('nodes'):
                    if n:
                        node = Node(nome=n.get('nome'), descricao=n.get('descricao'), label_template=n.get('label_template'), x=n.get('x'), y=n.get('y'), icone=n.get('icone'), classe=n.get('classe'), indicador=n.get('indicador'), mapa=mapa)

                        nodes_para_add.append(node)

                # Adicionando nodes em massa
                Node.objects.bulk_create(nodes_para_add, ignore_conflicts=True)

                # Importando edges
                for e in js.get('edges'):
                    if e:
                        source = Node.objects.get(nome=e.get('source__nome'), mapa_id=mapa)
                        target = Node.objects.get(nome=e.get('target__nome'), mapa_id=mapa)
                        edge = Edge(nome=e.get('nome'), descricao=e.get('descricao'), source=source, target=target, label_template=e.get('label_template'), indicador=e.get('indicador'), mapa=mapa)

                        edges_para_add.append(edge)

                # Adicionando edges em massa
                Edge.objects.bulk_create(edges_para_add, ignore_conflicts=True)

                res = HttpResponse('')
                res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Mapa importado com sucesso!', 'resultado': 'ok', 'cor': 'success'}, 'atualiza': 'atualizando mapa'})
                return res

        except Exception as e:
            print(f'Arquivo invalido com erro: {e}')

            res = render(template_name='beeapi/mapa_import.html', request=request, context=dados)
            res['HX-Trigger'] = json.dumps({'toast': {'mensagem': 'Erro ao importar mapa!', 'resultado': 'erro', 'cor': 'danger'}, 'atualiza': 'atualizando mapa'})
            return res

    return render(template_name='beeapi/mapa_import.html', request=request, context=dados)


