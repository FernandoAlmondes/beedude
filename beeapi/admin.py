from django.contrib import admin, messages
from django.shortcuts import redirect
from .models import Servidor, Mapa, Node, Edge, MapaGrupo
# Register your models here.

class ServidorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'url', 'status']
    list_filter = ['status']
    search_fields = ['nome', 'url']
admin.site.register(Servidor, ServidorAdmin)

class MapaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'servidor', 'status', 'default', 'autor__username']
    list_filter = ['status', 'autor__username']
    search_fields = ['nome', 'servidor__nome', 'autor__username']

    # Sobrescrevendo a view de delete do django admin pra evitar exclusao do ultimo mapa
    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)

        if obj and Mapa.objects.count() <= 1:
            self.message_user(
                request,
                "Você não pode remover todos os mapas!",
                level=messages.ERROR
            )
            return redirect(request.META.get("HTTP_REFERER", "../"))

        return super().delete_view(request, object_id, extra_context)

admin.site.register(Mapa, MapaAdmin)

class NodeAdmin(admin.ModelAdmin):
    list_display = ['nome', 'x', 'y', 'icone', 'classe', 'mapa__nome', 'mapa__servidor']
    list_filter = ['mapa']
    search_fields = ['nome']
admin.site.register(Node, NodeAdmin)

class EdgeAdmin(admin.ModelAdmin):
    list_display = ['nome', 'source', 'target', 'mapa__nome', 'mapa__servidor']
    list_filter = ['mapa']
    search_fields = ['nome', 'source__nome', 'target__nome']
admin.site.register(Edge, EdgeAdmin)

class MapaGrupoAdmin(admin.ModelAdmin):
    list_display = ['grupo', 'mostrar_mapas']
    list_filter = ['grupo']
    search_fields = ['grupo__name', 'mapa__nome']

    def mostrar_mapas(self, obj):
        return ", ".join(f'{mapa.nome}' for mapa in obj.mapa.all())

    mostrar_mapas.short_description = 'Mapas'

admin.site.register(MapaGrupo, MapaGrupoAdmin)