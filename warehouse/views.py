import csv

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .forms import (
    ArtworkForm,
    ArtworkMovementForm,
    WarehouseActivityForm,
    WarehouseFollowUpForm,
    WarehouseStockItemForm,
)
from .models import Artwork, ArtworkMovement, WarehouseActivity, WarehouseFollowUp, WarehouseStockItem


def can_manage_warehouse(user):
    return bool(getattr(user, 'can_operate_warehouse', False))


class WarehouseOperatorRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not can_manage_warehouse(request.user):
            messages.error(request, 'A area de almoxarifado e reservada para operadores autorizados.')
            return redirect('feed')
        return super().dispatch(request, *args, **kwargs)


def filtered_artworks(query):
    artworks = Artwork.objects.filter(is_active=True)
    query = (query or '').strip()
    if query:
        artworks = artworks.filter(
            Q(name__icontains=query)
            | Q(inventory_number__icontains=query)
            | Q(author__icontains=query)
            | Q(storage_location__icontains=query)
        )
    return artworks


class WarehouseDashboardView(WarehouseOperatorRequiredMixin, TemplateView):
    template_name = 'warehouse/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        today = timezone.localdate()
        month_start = today.replace(day=1)
        artworks = filtered_artworks(query).annotate(
            movement_total=Count('movements', distinct=True),
            followup_total=Count('followups', distinct=True),
        )
        open_movements = ArtworkMovement.objects.filter(
            movement_type=ArtworkMovement.MovementType.CHECK_OUT,
            returned_at__isnull=True,
        ).select_related('artwork')

        context['query'] = query
        context['artwork_form'] = kwargs.get('artwork_form') or ArtworkForm()
        context['movement_form'] = kwargs.get('movement_form') or ArtworkMovementForm()
        context['activity_form'] = kwargs.get('activity_form') or WarehouseActivityForm()
        context['followup_form'] = kwargs.get('followup_form') or WarehouseFollowUpForm()
        context['stock_form'] = kwargs.get('stock_form') or WarehouseStockItemForm()
        context['artworks'] = artworks[:30]
        context['open_movements'] = open_movements[:20]
        context['recent_movements'] = ArtworkMovement.objects.select_related('artwork')[:12]
        context['activities'] = WarehouseActivity.objects.select_related('artwork')[:12]
        context['followups'] = WarehouseFollowUp.objects.select_related('artwork')[:12]
        context['stock_items'] = WarehouseStockItem.objects.all()[:30]
        context['artwork_total'] = Artwork.objects.filter(is_active=True).count()
        context['today_activity_total'] = WarehouseActivity.objects.filter(activity_date=today).count()
        context['month_followup_total'] = WarehouseFollowUp.objects.filter(followup_date__gte=month_start).count()
        context['stock_attention_total'] = sum(1 for item in WarehouseStockItem.objects.all() if item.needs_attention or item.expires_soon)
        context['overdue_movement_total'] = sum(1 for movement in open_movements if movement.is_overdue)
        return context


class ArtworkCreateView(WarehouseOperatorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = ArtworkForm(request.POST, request.FILES)
        if form.is_valid():
            artwork = form.save(commit=False)
            artwork.created_by = request.user
            artwork.save()
            messages.success(request, f'Quadro {artwork.name} cadastrado no acervo.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect('warehouse-dashboard')


class ArtworkMovementCreateView(WarehouseOperatorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = ArtworkMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.created_by = request.user
            if not movement.operator_name:
                movement.operator_name = request.user.display_name or request.user.username
            movement.save()
            if movement.movement_type == ArtworkMovement.MovementType.CHECK_IN:
                open_movement = ArtworkMovement.objects.filter(
                    artwork=movement.artwork,
                    movement_type=ArtworkMovement.MovementType.CHECK_OUT,
                    returned_at__isnull=True,
                ).exclude(pk=movement.pk).order_by('-movement_date', '-created_at').first()
                if open_movement:
                    open_movement.mark_returned()
            messages.success(request, f'Movimentacao registrada para {movement.artwork.name}.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect('warehouse-dashboard')


class ArtworkMovementReturnView(WarehouseOperatorRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        movement = get_object_or_404(
            ArtworkMovement.objects.select_related('artwork'),
            pk=pk,
            movement_type=ArtworkMovement.MovementType.CHECK_OUT,
            returned_at__isnull=True,
        )
        movement.mark_returned()
        messages.success(request, f'Devolucao confirmada para {movement.artwork.name}.')
        return redirect('warehouse-dashboard')


class WarehouseActivityCreateView(WarehouseOperatorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = WarehouseActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.created_by = request.user
            activity.save()
            messages.success(request, f'Atividade criada para {activity.artwork.name}.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect('warehouse-dashboard')


class WarehouseFollowUpCreateView(WarehouseOperatorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = WarehouseFollowUpForm(request.POST)
        if form.is_valid():
            followup = form.save(commit=False)
            followup.created_by = request.user
            followup.save()
            messages.success(request, f'Acompanhamento salvo para {followup.artwork.name}.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect('warehouse-dashboard')


class WarehouseStockItemCreateView(WarehouseOperatorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = WarehouseStockItemForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            stock_item, created = WarehouseStockItem.objects.update_or_create(
                material=data['material'],
                batch=data['batch'],
                defaults={
                    'item_class': data['item_class'],
                    'unit': data['unit'],
                    'quantity': data['quantity'],
                    'minimum_quantity': data['minimum_quantity'],
                    'expiry_date': data['expiry_date'],
                    'location': data['location'],
                    'notes': data['notes'],
                    'created_by': request.user,
                },
            )
            action = 'cadastrado' if created else 'atualizado'
            messages.success(request, f'Item {stock_item.material} {action} no estoque.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect('warehouse-dashboard')


class WarehouseCsvExportView(WarehouseOperatorRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="almoxarifado-acervo.csv"'
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['id', 'obra', 'numero_quadro', 'autor', 'local', 'foto', 'observacoes'])
        for artwork in Artwork.objects.filter(is_active=True).order_by('name', 'inventory_number'):
            writer.writerow(
                [
                    artwork.pk,
                    artwork.name,
                    artwork.inventory_number,
                    artwork.author,
                    artwork.storage_location,
                    artwork.photo.name if artwork.photo else '',
                    artwork.notes,
                ]
            )
        return response
