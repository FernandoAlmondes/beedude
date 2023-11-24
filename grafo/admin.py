from django.contrib import admin

from .models import Elemento, Item, Cliente, Mapa, Servidor

# Register your models here.

#admin.site.register(Node)
#admin.site.register(Edge)

class ElementoAdmin(admin.ModelAdmin):
    list_display = ['codigo','label','status','rxbits','txbits','node','host_a','host_b','horario','mapa']
    list_filter = ['node','status','mapa']
    search_fields = ['codigo','label']
    autocomplete_fields = ['host_a','host_b','rxbits','txbits','status_item','mapa']
    ordering = ['-node']
    fieldsets = [
        ('Geral', {'fields': ['codigo', 'label', 'status','mapa']}),
        ('Arestas', {'fields': ['host_a', 'host_b']}),
        ('Interfaces', {'fields': ['txbits', 'rxbits', 'status_item']}),
        ('Outros', {'fields': ['node', 'horario']}),
    ]

admin.site.register(Elemento, ElementoAdmin)

# class EdgeAdmin(admin.ModelAdmin):
#     #list_display = [field.name for field in Elemento._meta.get_fields()]
#     #list_filter = ['node','label','codigo']
#     ordering = ['-nome']
#
# admin.site.register(Edge, EdgeAdmin)

class ItemAdmin(admin.ModelAdmin):
    list_display = ['itemid','nome','status','valor','horario']
    search_fields = ['nome','itemid']
    #list_filter = ['node','label','codigo']
    ordering = ['-nome']

admin.site.register(Item, ItemAdmin)

class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nome','cpf_cnpj','habilitado']
    search_fields = ['nome','cpf_cnpj']
    list_filter = ['habilitado']
    ordering = ['-nome']

admin.site.register(Cliente, ClienteAdmin)

class MapaAdmin(admin.ModelAdmin):
    list_display = ['nome','cliente','horario']
    search_fields = ['nome','cliente']
    list_filter = ['habilitado']
    ordering = ['-nome']

admin.site.register(Mapa, MapaAdmin)

class ServidorAdmin(admin.ModelAdmin):
    list_display = ['nome','url','habilitado']
    search_fields = ['nome','url']
    list_filter = ['habilitado']
    ordering = ['-nome']

    def has_add_permission(self, request):
        if Servidor.objects.exists():
            return False
        return True

admin.site.register(Servidor, ServidorAdmin)