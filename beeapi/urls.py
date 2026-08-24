from django.contrib import admin
from django.urls import path
from django.contrib.auth.decorators import login_required

from .views import mapaImport, mapaExport, retorna_grafico, retorna_historico, modo, edita_itens_triggers, index, dados, listaMapa, addMapa, mapaEdit, listaNode, addNode, nodeEdit, salvar_posicao, listaEdge, addEdge, edgeEdit, consulta_grupos, consulta_hosts, consulta_itens_triggers, consulta_itens, consulta_triggers, integracao_inicio, integracao_revisao

urlpatterns = [
    path('', view=login_required(index), name='index'),
    path('dados/<int:mapaid>', view=login_required(dados), name='dados'),
    path('mapas/', view=login_required(listaMapa), name='mapa_listagem'),
    path('mapas/add', view=login_required(addMapa), name='mapa_add'),
    path('mapas/<int:id>', view=login_required(mapaEdit), name='mapa_editar'),
    path('nodes/', view=login_required(listaNode), name='node_listagem'),
    path('nodes/add', view=login_required(addNode), name='node_add'),
    path('nodes/posicao', view=login_required(salvar_posicao), name='node_posicao'),
    path('nodes/<str:nodeid>', view=login_required(nodeEdit), name='node_editar'),
    path('edges/', view=login_required(listaEdge), name='edge_listagem'),
    path('edges/add', view=login_required(addEdge), name='edge_add'),
    path('edges/<str:edgeid>', view=login_required(edgeEdit), name='edge_editar'),
    path('consulta_grupos/', view=login_required(consulta_grupos), name='consulta_grupos'),
    path('consulta_hosts/', view=login_required(consulta_hosts), name='consulta_hosts'),
    path('consulta_itens_triggers/', view=login_required(consulta_itens_triggers), name='consulta_itens_triggers'),
    path('consulta_itens/', view=login_required(consulta_itens), name='consulta_itens'),
    path('consulta_triggers/', view=login_required(consulta_triggers), name='consulta_triggers'),
    path('integracao_revisao/', view=login_required(integracao_revisao), name='integracao_revisao'),
    path('integracao/', view=login_required(integracao_inicio), name='integracao_inicio'),
    path('edita_itens_triggers/', view=login_required(edita_itens_triggers), name='edita_itens_triggers'),
    path('modo/', view=login_required(modo), name='modo'),
    path('historico/', view=login_required(retorna_historico), name='historico'),
    path('grafico/', view=login_required(retorna_grafico), name='grafico'),
    path('mapa/export/<int:mapaid>', view=login_required(mapaExport), name='mapa_export'),
    path('mapa/import/', view=login_required(mapaImport), name='mapa_import')

]