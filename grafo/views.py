from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm
from django.contrib import messages

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Count

# Create your views here.

from .models import Elemento, Mapa, Item, Servidor


from django.http import JsonResponse

def bits_to_human_readable(bits):
    """
    Converte bits para uma representação mais legível em kbps, Mbps ou Gbps.
    """
    if bits is None:
        return ''

    # Convertendo para kbps se for menor que 1 Mbps
    if bits < 1e6:
        return f"{bits / 1e3:.2f} kbps"
    # Convertendo para Mbps se for menor que 1 Gbps
    elif bits < 1e9:
        return f"{bits / 1e6:.2f} Mbps"
    else:
        # Convertendo para Gbps se for maior ou igual a 1 Gbps
        return f"{bits / 1e9:.2f} Gbps"

@login_required
def logout_view(request):
    logout(request)
    return redirect('mapa-list')

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('mapa-list')
            else:
                messages.error(request, 'Credenciais inválidas. Por favor, tente novamente.')


    else:
        form = LoginForm()

    return render(request, 'grafo/login.html', {'form': form})


@login_required
def beedude(request, pk):

    mapa_id = get_object_or_404(Mapa, pk=pk)

    elementos = Elemento.objects.filter(mapa=mapa_id)
    servidor = Servidor.objects.first()

    if servidor:
        servidor = servidor.url
    else:
        servidor = 'http://127.0.0.1'

    dados = {
        "elementos": [
            {
                'id': elemento.id,
                'codigo': elemento.codigo,
                'label': elemento.label,
                'status': elemento.status,
                'host_a_id': elemento.host_a.codigo if elemento.host_a else '',
                'host_b_id': elemento.host_b.codigo if elemento.host_b else '',
                'host_a_status': elemento.host_a.status if elemento.host_a else 0,
                'host_b_status': elemento.host_b.status if elemento.host_b else 0,
                'rxbits_id': bits_to_human_readable(elemento.rxbits.valor) if elemento.rxbits else '',
                'txbits_id': bits_to_human_readable(elemento.txbits.valor) if elemento.txbits else '',
                'rxbits_name': elemento.rxbits.nome if elemento.rxbits else '',
                'txbits_name': elemento.txbits.nome if elemento.txbits else '',
                'status_item': elemento.status_item.status if elemento.status_item else '',
                'status_item_nome': elemento.status_item.nome if elemento.status_item else '',
                'node': 1 if elemento.node else 0,
            }
            for elemento in elementos
        ], "servidor": servidor,
    }
    #print(dados)
    return render(request, 'grafo/mapa.html', {'dados': dados})

class MapaListView(ListView):
    model = Mapa
    template_name = 'grafo/mapa_list.html'

    context_object_name = 'dados'

    def get_queryset(self):

        context = {}

        context['mapas'] = Mapa.objects.all()
        context['elementos'] = Elemento.objects.all()

        context['mapas_total'] = Mapa.objects.all().count()
        context['elementos_total'] = Elemento.objects.all().count()
        context['items_total'] = Item.objects.all().count()
        #print(context)
        return context
