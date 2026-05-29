from django.urls import path

from .views import (
    ArtworkCreateView,
    ArtworkMovementCreateView,
    ArtworkMovementReturnView,
    WarehouseActivityCreateView,
    WarehouseCsvExportView,
    WarehouseDashboardView,
    WarehouseFollowUpCreateView,
    WarehouseStockItemCreateView,
)


urlpatterns = [
    path('', WarehouseDashboardView.as_view(), name='warehouse-dashboard'),
    path('acervo/criar/', ArtworkCreateView.as_view(), name='warehouse-artwork-create'),
    path('movimentacoes/criar/', ArtworkMovementCreateView.as_view(), name='warehouse-movement-create'),
    path('movimentacoes/<int:pk>/devolver/', ArtworkMovementReturnView.as_view(), name='warehouse-movement-return'),
    path('atividades/criar/', WarehouseActivityCreateView.as_view(), name='warehouse-activity-create'),
    path('acompanhamentos/criar/', WarehouseFollowUpCreateView.as_view(), name='warehouse-followup-create'),
    path('estoque/criar/', WarehouseStockItemCreateView.as_view(), name='warehouse-stock-create'),
    path('exportar/acervo.csv', WarehouseCsvExportView.as_view(), name='warehouse-csv-export'),
]
