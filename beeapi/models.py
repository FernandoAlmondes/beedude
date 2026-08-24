from django.db import models
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group, User

import uuid

# Create your models here.

def retorna_uuid():
    return str(uuid.uuid4())

icones = [
    ('bee-router', 'bee-router'),
    ('bee-switch', 'bee-switch'),
    ('bee-network-wired', 'bee-network-wired'),
    ('bee-server', 'bee-server'),
    ('bee-circle-dot', 'bee-circle-dot'),
    ('bee-cloud', 'bee-cloud')
]

classes = [
    ('node', 'node'),
    ('label', 'label'),
    ('nota', 'nota'),
    ('marcador', 'marcador')
]

class Servidor(models.Model):
    nome = models.CharField(max_length=200, unique=True)
    url = models.CharField(max_length=200, unique=True)
    token = models.CharField(max_length=200, unique=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name_plural = 'Servidores'

class Mapa(models.Model):
    nome = models.CharField(max_length=200, unique=True)
    descricao = models.TextField(blank=True, null=True)
    servidor = models.ForeignKey(Servidor, on_delete=models.CASCADE)
    data = models.JSONField(null=True, blank=True)
    status = models.BooleanField(default=True)
    default = models.BooleanField(default=False)
    autor = models.ForeignKey(User, on_delete=models.CASCADE, null=True, editable=False)

    def __str__(self):
        return self.nome
    
    # Regra para sempre que um novo dashboard for marcado como default o antigo seja desmarcado
    def save(self, *args, **kwargs):
        with transaction.atomic(): # Usamos o atomic para evitar caso duas transacoes de default cheguem ao mesmo tempo
            if self.default:
                Mapa.objects.filter(default=True).update(default=False)
            super().save(*args, **kwargs)

class Node(models.Model):
    nodeid = models.CharField(max_length=200, default=retorna_uuid, editable=False, unique=True)
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    label_template = models.TextField(blank=True, null=True)
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    icone = models.CharField(max_length=100, null=True, blank=True, default='bee-server', choices=icones)
    classe = models.CharField(max_length=100, blank=True, null=True, default='node', choices=classes)
    indicador = models.JSONField(blank=True, null=True)
    mapa = models.ForeignKey(Mapa, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome

    # Nome do node pode ser igual em mapas diferentes.
    class Meta:
        constraints = [models.UniqueConstraint(fields=['nome', 'mapa'], name='unique_node_nome_mapa')]

class Edge(models.Model):
    edgeid = models.CharField(max_length=200, default=retorna_uuid, editable=False, unique=True)
    nome = models.CharField(max_length=200, blank=True, null=True)
    descricao = models.TextField(blank=True, null=True)
    label_template = models.TextField(blank=True, null=True)
    source = models.ForeignKey(Node, models.CASCADE, related_name='nodeids', to_field='nodeid')
    target = models.ForeignKey(Node, models.CASCADE, related_name='nodeidt', to_field='nodeid')
    indicador = models.JSONField(blank=True, null=True)
    mapa = models.ForeignKey(Mapa, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome
    
    # Nome do edge pode ser igual em mapas diferentes.
    class Meta:
        constraints = [models.UniqueConstraint(fields=['nome', 'mapa'], name='unique_edge_nome_mapa')]

class MapaGrupo(models.Model):
    mapa = models.ManyToManyField(Mapa, blank=True, related_name="grupos_mapas")
    grupo = models.ForeignKey(Group, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Grupos de Mapas'