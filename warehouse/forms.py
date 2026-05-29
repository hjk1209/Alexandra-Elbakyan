from django import forms

from core.security import clean_plain_text
from core.uploads import validate_safe_image_upload

from .models import Artwork, ArtworkMovement, WarehouseActivity, WarehouseFollowUp, WarehouseStockItem


def active_artwork_queryset():
    return Artwork.objects.filter(is_active=True).order_by('name', 'inventory_number')


class ArtworkForm(forms.ModelForm):
    class Meta:
        model = Artwork
        fields = (
            'name',
            'inventory_number',
            'author',
            'storage_location',
            'photo',
            'condition_notes',
            'notes',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'Nome da obra'
        self.fields['inventory_number'].label = 'Numero do quadro / ID'
        self.fields['author'].label = 'Nome do autor'
        self.fields['storage_location'].label = 'Local de armazenamento'
        self.fields['photo'].label = 'Foto do quadro'
        self.fields['photo'].required = False
        self.fields['photo'].help_text = 'Opcional. Envie JPG, PNG ou WEBP de ate 6 MB.'
        self.fields['condition_notes'].label = 'Estado de conservacao'
        self.fields['notes'].label = 'Observacoes gerais'

    def clean_name(self):
        return clean_plain_text(self.cleaned_data['name'])

    def clean_inventory_number(self):
        return clean_plain_text(self.cleaned_data['inventory_number']).upper()

    def clean_author(self):
        return clean_plain_text(self.cleaned_data.get('author', ''))

    def clean_storage_location(self):
        return clean_plain_text(self.cleaned_data.get('storage_location', ''))

    def clean_condition_notes(self):
        return clean_plain_text(self.cleaned_data.get('condition_notes', ''))

    def clean_notes(self):
        return clean_plain_text(self.cleaned_data.get('notes', ''))

    def clean_photo(self):
        return validate_safe_image_upload(self.cleaned_data.get('photo'), max_size_mb=6, field_label='Foto do quadro')


class ArtworkMovementForm(forms.ModelForm):
    class Meta:
        model = ArtworkMovement
        fields = (
            'movement_date',
            'movement_type',
            'artwork',
            'taken_by',
            'phone_number',
            'class_group',
            'cpp_responsible',
            'operator_name',
            'due_date',
            'notes',
        )
        widgets = {
            'movement_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['artwork'].queryset = active_artwork_queryset()
        self.fields['movement_date'].label = 'Data'
        self.fields['movement_type'].label = 'Tipo'
        self.fields['artwork'].label = 'Quadro do acervo'
        self.fields['taken_by'].label = 'Nome de quem pegou'
        self.fields['phone_number'].label = 'Telefone'
        self.fields['class_group'].label = 'Turma'
        self.fields['cpp_responsible'].label = 'CPP responsavel'
        self.fields['operator_name'].label = 'Operadora'
        self.fields['due_date'].label = 'Prazo de devolucao'
        self.fields['notes'].label = 'Observacoes'

    def clean_taken_by(self):
        return clean_plain_text(self.cleaned_data['taken_by'])

    def clean_phone_number(self):
        return clean_plain_text(self.cleaned_data.get('phone_number', ''))

    def clean_class_group(self):
        return clean_plain_text(self.cleaned_data.get('class_group', ''))

    def clean_cpp_responsible(self):
        return clean_plain_text(self.cleaned_data.get('cpp_responsible', ''))

    def clean_operator_name(self):
        return clean_plain_text(self.cleaned_data.get('operator_name', ''))

    def clean_notes(self):
        return clean_plain_text(self.cleaned_data.get('notes', ''))


class WarehouseActivityForm(forms.ModelForm):
    class Meta:
        model = WarehouseActivity
        fields = ('activity_date', 'activity_time', 'artwork', 'activity_type', 'responsible', 'status', 'notes')
        widgets = {
            'activity_date': forms.DateInput(attrs={'type': 'date'}),
            'activity_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['artwork'].queryset = active_artwork_queryset()
        self.fields['activity_date'].label = 'Data'
        self.fields['activity_time'].label = 'Hora'
        self.fields['artwork'].label = 'Obra / quadro'
        self.fields['activity_type'].label = 'Tipo'
        self.fields['responsible'].label = 'Responsavel'
        self.fields['status'].label = 'Status'
        self.fields['notes'].label = 'Observacoes'

    def clean_responsible(self):
        return clean_plain_text(self.cleaned_data.get('responsible', ''))

    def clean_notes(self):
        return clean_plain_text(self.cleaned_data.get('notes', ''))


class WarehouseFollowUpForm(forms.ModelForm):
    class Meta:
        model = WarehouseFollowUp
        fields = (
            'followup_date',
            'followup_time',
            'artwork',
            'responsible',
            'reason',
            'action_taken',
            'support_material',
            'return_date',
            'status',
            'destination',
        )
        widgets = {
            'followup_date': forms.DateInput(attrs={'type': 'date'}),
            'followup_time': forms.TimeInput(attrs={'type': 'time'}),
            'return_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['artwork'].queryset = active_artwork_queryset()
        self.fields['followup_date'].label = 'Data'
        self.fields['followup_time'].label = 'Hora'
        self.fields['artwork'].label = 'Obra / quadro'
        self.fields['responsible'].label = 'Responsavel'
        self.fields['reason'].label = 'Motivo do acompanhamento'
        self.fields['action_taken'].label = 'Acao realizada'
        self.fields['support_material'].label = 'Material ou apoio utilizado'
        self.fields['return_date'].label = 'Data de retorno'
        self.fields['status'].label = 'Status'
        self.fields['destination'].label = 'Encaminhamento / local de uso'

    def clean_responsible(self):
        return clean_plain_text(self.cleaned_data['responsible'])

    def clean_reason(self):
        return clean_plain_text(self.cleaned_data.get('reason', ''))

    def clean_action_taken(self):
        return clean_plain_text(self.cleaned_data.get('action_taken', ''))

    def clean_support_material(self):
        return clean_plain_text(self.cleaned_data.get('support_material', ''))

    def clean_destination(self):
        return clean_plain_text(self.cleaned_data.get('destination', ''))


class WarehouseStockItemForm(forms.ModelForm):
    class Meta:
        model = WarehouseStockItem
        fields = (
            'material',
            'item_class',
            'batch',
            'unit',
            'quantity',
            'minimum_quantity',
            'expiry_date',
            'location',
            'notes',
        )
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['material'].label = 'Material'
        self.fields['item_class'].label = 'Classe'
        self.fields['batch'].label = 'Lote'
        self.fields['unit'].label = 'Unidade'
        self.fields['quantity'].label = 'Quantidade atual'
        self.fields['minimum_quantity'].label = 'Quantidade minima'
        self.fields['expiry_date'].label = 'Validade'
        self.fields['location'].label = 'Localizacao'
        self.fields['notes'].label = 'Observacoes'

    def clean_material(self):
        return clean_plain_text(self.cleaned_data['material'])

    def clean_item_class(self):
        return clean_plain_text(self.cleaned_data.get('item_class', ''))

    def clean_batch(self):
        return clean_plain_text(self.cleaned_data['batch'])

    def clean_location(self):
        return clean_plain_text(self.cleaned_data.get('location', ''))

    def clean_notes(self):
        return clean_plain_text(self.cleaned_data.get('notes', ''))
