from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Artwork, ArtworkMovement, WarehouseStockItem


class WarehouseFlowTests(TestCase):
    password = 'SenhaSegura!2026'

    def setUp(self):
        self.operator = User.objects.create_user(
            username='almox.operadora',
            display_name='Operadora Almox',
            handle='almox_operadora',
            email='almox@example.com',
            birth_date='1991-01-01',
            is_warehouse_operator=True,
            password=self.password,
        )
        self.regular = User.objects.create_user(
            username='regular',
            display_name='Regular',
            handle='regular',
            email='regular@example.com',
            birth_date='2000-01-01',
            password=self.password,
        )

    def test_regular_user_cannot_open_warehouse_dashboard(self):
        self.client.force_login(self.regular)
        response = self.client.get(reverse('warehouse-dashboard'))
        self.assertRedirects(response, reverse('feed'))

    def test_operator_can_create_artwork_and_view_protected_photo(self):
        self.client.force_login(self.operator)
        response = self.client.post(
            reverse('warehouse-artwork-create'),
            {
                'name': 'Memoria da Escola',
                'inventory_number': 'QD-100',
                'author': 'Autoria Coletiva',
                'storage_location': 'Sala 2',
                'condition_notes': 'Bom estado',
                'notes': 'Quadro usado em exposicao.',
                'photo': SimpleUploadedFile('quadro.jpg', b'image-content', content_type='image/jpeg'),
            },
        )
        self.assertRedirects(response, reverse('warehouse-dashboard'))
        artwork = Artwork.objects.get(inventory_number='QD-100')
        self.assertEqual(artwork.created_by, self.operator)

        response = self.client.get(artwork.photo_view_url)
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.regular)
        response = self.client.get(artwork.photo_view_url)
        self.assertEqual(response.status_code, 404)

    def test_operator_can_register_checkout_and_return(self):
        artwork = Artwork.objects.create(
            name='Territorio Vivo',
            inventory_number='QD-200',
            author='Coletivo',
            storage_location='Corredor',
            created_by=self.operator,
        )
        self.client.force_login(self.operator)
        response = self.client.post(
            reverse('warehouse-movement-create'),
            {
                'movement_date': timezone.localdate().isoformat(),
                'movement_type': ArtworkMovement.MovementType.CHECK_OUT,
                'artwork': artwork.pk,
                'taken_by': 'Joana Silva',
                'phone_number': '(11) 99999-0000',
                'class_group': 'Oficina',
                'cpp_responsible': 'CPP Maria',
                'operator_name': 'Operadora',
                'due_date': (timezone.localdate() + timezone.timedelta(days=7)).isoformat(),
                'notes': 'Saiu para atividade.',
            },
        )
        self.assertRedirects(response, reverse('warehouse-dashboard'))
        movement = ArtworkMovement.objects.get(artwork=artwork)
        self.assertTrue(movement.is_open)

        response = self.client.post(reverse('warehouse-movement-return', args=[movement.pk]))
        self.assertRedirects(response, reverse('warehouse-dashboard'))
        movement.refresh_from_db()
        self.assertFalse(movement.is_open)
        self.assertIsNotNone(movement.returned_at)

    def test_operator_can_create_stock_and_export_csv(self):
        self.client.force_login(self.operator)
        response = self.client.post(
            reverse('warehouse-stock-create'),
            {
                'material': 'Papel A4',
                'item_class': 'Secretaria',
                'batch': 'PM-08',
                'unit': WarehouseStockItem.Unit.BOXES,
                'quantity': '14',
                'minimum_quantity': '6',
                'expiry_date': '',
                'location': 'Armario C',
                'notes': 'Material de catalogacao.',
            },
        )
        self.assertRedirects(response, reverse('warehouse-dashboard'))
        self.assertTrue(WarehouseStockItem.objects.filter(material='Papel A4', batch='PM-08').exists())

        Artwork.objects.create(name='Raizes', inventory_number='QD-300', created_by=self.operator)
        response = self.client.get(reverse('warehouse-csv-export'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'QD-300')
