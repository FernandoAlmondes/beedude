from django.db import models

# Create your models here.

from django.db import models
from django.contrib.auth.models import User

class Servidor(models.Model):
    nome = models.CharField(max_length=200, null=True, blank=True)
    url = models.CharField(max_length=100, null=True, blank=True)
    habilitado = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Servidor'
        verbose_name_plural = 'Servidores'

    def __str__(self):
        return str(self.nome)

class Cliente(models.Model):
    nome = models.CharField(max_length=200, null=True, blank=True)
    cpf_cnpj = models.CharField(max_length=100, null=True, blank=True)
    habilitado = models.BooleanField(default=True)

    def __str__(self):
        return str(self.nome)

class Mapa(models.Model):
    nome = models.CharField(max_length=200, null=True, blank=True)
    descricao = models.TextField(null=True, blank=True, default='Mapa criado com o Beedude.')
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, blank=True, null=True)
    user = models.ManyToManyField(User)
    horario = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    habilitado = models.BooleanField(default=True)

    def __str__(self):
        return str(self.nome)

class Item(models.Model):
    nome = models.CharField(max_length=400, null=True, blank=True)
    itemid = models.IntegerField(null=True, blank=True)
    status = models.IntegerField(null=True, blank=True)
    valor = models.FloatField(null=True, blank=True)
    horario = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.nome)

class Elemento(models.Model):
    codigo = models.CharField(max_length=400, null=True, blank=True)
    label = models.CharField(max_length=400, null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True, default=1)
    host_a = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='host_a_self', null=True, blank=True, default='')
    host_b = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='host_b_self', null=True, blank=True, default='')
    #rxbits = models.IntegerField(null=True, blank=True)
    txbits = models.ForeignKey(Item, on_delete=models.SET_NULL, related_name='txbits_item', null=True, blank=True)
    rxbits = models.ForeignKey(Item, on_delete=models.SET_NULL, related_name='rxbits_item', null=True, blank=True)
    status_item = models.ForeignKey(Item, on_delete=models.SET_NULL, related_name='status_item', null=True, blank=True)
    #txbits = models.IntegerField(null=True, blank=True)
    node = models.BooleanField(default=False)
    horario = models.DateTimeField(null=True, blank=True)
    mapa = models.ForeignKey(Mapa, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return str(self.label)