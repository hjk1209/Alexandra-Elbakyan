from django import forms

from accounts.models import User
from core.security import clean_plain_text
from core.uploads import validate_safe_document_upload, validate_safe_image_upload

from .models import ActivityReport, Post, Story


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('caption', 'media', 'visibility', 'allow_download', 'allow_sharing', 'age_rating')
        widgets = {
            'caption': forms.Textarea(attrs={'rows': 4, 'placeholder': 'O que move a juventude hoje?'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['age_rating'].required = False
        self.fields['age_rating'].initial = Post.AgeRating.FREE
        self.fields['allow_sharing'].initial = True

    def clean_caption(self):
        return clean_plain_text(self.cleaned_data.get('caption', ''))

    def clean_media(self):
        return validate_safe_image_upload(self.cleaned_data.get('media'), max_size_mb=4, field_label='Midia da postagem')


class StoryForm(forms.ModelForm):
    allowed_viewers = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        label='Lista de quem pode ver',
        widget=forms.SelectMultiple(attrs={'size': 6}),
    )
    allowed_responders = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        label='Lista de quem pode responder',
        widget=forms.SelectMultiple(attrs={'size': 6}),
    )

    class Meta:
        model = Story
        fields = (
            'caption',
            'media',
            'background_style',
            'visibility',
            'allow_download',
            'allowed_viewers',
            'reply_scope',
            'allowed_responders',
            'music_label',
            'music_url',
            'age_rating',
            'duration_hours',
        )
        widgets = {
            'caption': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': 'Conte o momento, escreva no story ou chame para a acao.',
                }
            ),
            'music_label': forms.TextInput(attrs={'placeholder': 'Nome da musica ou artista'}),
            'music_url': forms.URLInput(attrs={'placeholder': 'Link da musica, clipe ou player'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['age_rating'].required = False
        self.fields['age_rating'].initial = Story.AgeRating.FREE
        queryset = User.objects.filter(is_active=True).exclude(pk=getattr(user, 'pk', None)).order_by(
            'display_name',
            'username',
        )
        self.fields['allowed_viewers'].queryset = queryset
        self.fields['allowed_responders'].queryset = queryset

    def clean_caption(self):
        return clean_plain_text(self.cleaned_data.get('caption', ''))

    def clean_music_label(self):
        return clean_plain_text(self.cleaned_data.get('music_label', ''))

    def clean_media(self):
        return validate_safe_image_upload(self.cleaned_data.get('media'), max_size_mb=4, field_label='Midia do story')

    def clean(self):
        cleaned_data = super().clean()
        visibility = cleaned_data.get('visibility')
        reply_scope = cleaned_data.get('reply_scope')
        allowed_viewers = cleaned_data.get('allowed_viewers')
        allowed_responders = cleaned_data.get('allowed_responders')

        if visibility == Story.Visibility.CUSTOM and not allowed_viewers:
            self.add_error('allowed_viewers', 'Selecione pelo menos um perfil para ver este story.')
        if reply_scope == Story.ReplyScope.CUSTOM and not allowed_responders:
            self.add_error('allowed_responders', 'Selecione pelo menos um perfil para responder este story.')
        return cleaned_data


class StoryReplyForm(forms.Form):
    body = forms.CharField(
        label='Responder',
        max_length=280,
        widget=forms.Textarea(
            attrs={
                'rows': 2,
                'placeholder': 'Responder ao story com respeito e objetividade',
            }
        ),
    )

    def clean_body(self):
        body = clean_plain_text(self.cleaned_data.get('body', ''))
        if not body:
            raise forms.ValidationError('Escreva algo para responder ao story.')
        return body


class ActivityReportForm(forms.ModelForm):
    class Meta:
        model = ActivityReport
        fields = ('community', 'title', 'activity_date', 'body', 'photo', 'attachment')
        widgets = {
            'activity_date': forms.DateInput(attrs={'type': 'date'}),
            'body': forms.Textarea(
                attrs={
                    'rows': 7,
                    'placeholder': 'Relate o que aconteceu, quem participou, encaminhamentos e proximos passos.',
                }
            ),
        }

    def __init__(self, *args, communities=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['community'].queryset = communities if communities is not None else User.objects.filter(
            is_active=True,
            role=User.Role.COLLECTIVE,
        ).order_by('display_name', 'username')
        self.fields['community'].label = 'Comunidade / NB'
        self.fields['community'].help_text = 'Escolha a comunidade que recebera a relatoria.'
        self.fields['title'].label = 'Titulo da atividade'
        self.fields['title'].widget.attrs.update({'placeholder': 'Ex.: Oficina de comunicacao da NB'})
        self.fields['activity_date'].label = 'Data da atividade'
        self.fields['body'].label = 'Texto da relatoria'
        self.fields['photo'].label = 'Foto da atividade'
        self.fields['photo'].required = False
        self.fields['photo'].help_text = 'Opcional. Envie JPG, PNG ou WEBP de ate 6 MB.'
        self.fields['attachment'].label = 'Arquivo de apoio'
        self.fields['attachment'].required = False
        self.fields['attachment'].help_text = 'Opcional. Aceita PDF, DOC, planilha, ODT, ODS, TXT ou CSV ate 12 MB.'

    def clean_title(self):
        return clean_plain_text(self.cleaned_data['title'])

    def clean_body(self):
        body = clean_plain_text(self.cleaned_data.get('body', ''))
        if not body:
            raise forms.ValidationError('Escreva o texto da relatoria.')
        return body

    def clean_photo(self):
        return validate_safe_image_upload(self.cleaned_data.get('photo'), max_size_mb=6, field_label='Foto da atividade')

    def clean_attachment(self):
        return validate_safe_document_upload(
            self.cleaned_data.get('attachment'),
            max_size_mb=12,
            field_label='Arquivo de apoio',
        )
