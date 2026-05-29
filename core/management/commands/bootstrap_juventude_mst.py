from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from health.models import HealthAppointment, HealthConsultation, HealthRecord, HealthUnit
from messaging.models import Conversation, Message
from social.models import CommunityNotice, Follow, GroupActivity, Post, WeeklyTask
from warehouse.models import Artwork, ArtworkMovement, WarehouseActivity, WarehouseFollowUp, WarehouseStockItem


DEMO_PASSWORD = 'MstJuventude!2026'


class Command(BaseCommand):
    help = 'Cria dados demonstrativos da rede social da juventude do MST.'

    def handle(self, *args, **options):
        users_data = [
            {
                'username': 'coord.juventude',
                'handle': 'coord_juventude',
                'display_name': 'Coordenacao da Juventude',
                'email': 'coord@rede-raizes-socialista.local',
                'birth_date': '1988-05-10',
                'role': User.Role.FOUNDER,
                'bio': 'Articulacao de frentes, brigadas e jornadas de formacao.',
                'location': 'Escola Nacional Florestan Fernandes',
                'avatar_url': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=600&q=80',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'brigada.campo',
                'handle': 'brigada_campo',
                'display_name': 'Brigada Campo Vivo',
                'email': 'campo@rede-raizes-socialista.local',
                'birth_date': '1995-08-21',
                'role': User.Role.COLLECTIVE,
                'bio': 'Mutiroes, agroecologia e comunicacao de base.',
                'location': 'Assentamento Terra Livre',
                'avatar_url': 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=600&q=80',
            },
            {
                'username': 'comunica.mst',
                'handle': 'comunica_mst',
                'display_name': 'Coletivo de Comunicacao',
                'email': 'comunica@rede-raizes-socialista.local',
                'birth_date': '1997-03-14',
                'role': User.Role.MODERATOR,
                'bio': 'Cobertura de jornadas, memoria e feed da comunidade.',
                'location': 'Recife',
                'avatar_url': 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=600&q=80',
                'is_rapporteur': True,
            },
            {
                'username': 'maria.raiz',
                'handle': 'maria_raiz',
                'display_name': 'Maria da Raiz',
                'email': 'maria@rede-raizes-socialista.local',
                'birth_date': '2001-11-07',
                'role': User.Role.MEMBER,
                'bio': 'Juventude, cultura popular e circulos de estudo.',
                'location': 'Fortaleza',
                'avatar_url': 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=600&q=80',
            },
            {
                'username': 'saude.unidade',
                'handle': 'saude_unidade',
                'display_name': 'Operadora da Unidade de Saude',
                'email': 'saude@rede-raizes-socialista.local',
                'birth_date': '1992-09-30',
                'role': User.Role.MEMBER,
                'bio': 'Acompanha consultas, prontuarios populares e agendamentos da unidade.',
                'location': 'Unidade de Saude Popular',
                'avatar_url': 'https://images.unsplash.com/photo-1544723795-3fb6469f5b39?auto=format&fit=crop&w=600&q=80',
                'is_health_operator': True,
            },
            {
                'username': 'almox.enff',
                'handle': 'almox_enff',
                'display_name': 'Operadora do Almoxarifado',
                'email': 'almox@rede-raizes-socialista.local',
                'birth_date': '1991-04-18',
                'role': User.Role.MEMBER,
                'bio': 'Controle de quadros, fotos, materiais e movimentacoes do acervo.',
                'location': 'Almoxarifado ENFF',
                'avatar_url': 'https://images.unsplash.com/photo-1553413077-190dd305871c?auto=format&fit=crop&w=600&q=80',
                'is_warehouse_operator': True,
            },
        ]

        created_users = {}
        for data in users_data:
            username = data['username']
            defaults = data.copy()
            defaults.pop('username')
            defaults['onboarding_completed'] = True
            user, _ = User.objects.update_or_create(username=username, defaults=defaults)
            user.set_password(DEMO_PASSWORD)
            user.save()
            created_users[username] = user

        Follow.objects.get_or_create(
            follower=created_users['maria.raiz'],
            following=created_users['comunica.mst'],
        )
        Follow.objects.get_or_create(
            follower=created_users['maria.raiz'],
            following=created_users['brigada.campo'],
        )
        Follow.objects.get_or_create(
            follower=created_users['brigada.campo'],
            following=created_users['coord.juventude'],
        )

        posts_data = [
            {
                'author': created_users['coord.juventude'],
                'caption': 'Abrimos a Rede Raizes Socialista para aproximar brigadas, escolas e coletivos de juventude.',
                'visibility': Post.Visibility.PUBLIC,
            },
            {
                'author': created_users['comunica.mst'],
                'caption': 'Cobertura da jornada de comunicacao: fotos, relatos e encaminhamentos ja estao no ar.',
                'visibility': Post.Visibility.COMMUNITY,
            },
            {
                'author': created_users['maria.raiz'],
                'caption': 'Quem cola no mutirao cultural de sabado? Quero reunir a turma para arte, debate e musica.',
                'visibility': Post.Visibility.FOLLOWERS,
            },
        ]

        for entry in posts_data:
            Post.objects.get_or_create(
                author=entry['author'],
                caption=entry['caption'],
                defaults={'visibility': entry['visibility']},
            )

        conversation, _ = Conversation.get_or_create_direct(
            created_users['maria.raiz'],
            created_users['comunica.mst'],
        )
        if not conversation.messages.exists():
            Message.objects.create(
                conversation=conversation,
                author=created_users['maria.raiz'],
                body='Compas, podemos divulgar o encontro de juventude no feed principal?',
            )
            Message.objects.create(
                conversation=conversation,
                author=created_users['comunica.mst'],
                body='Sim. Envia a arte final e o texto-base que a gente sobe hoje.',
            )

        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())

        notices_data = [
            {
                'title': 'Aviso geral da comunidade',
                'body': 'As brigadas devem atualizar a presenca nas atividades e confirmar quem participa do mutirao deste mes.',
                'author': created_users['coord.juventude'],
                'is_pinned': True,
            },
            {
                'title': 'Jornada cultural e comunicacao',
                'body': 'O grupo de comunicacao abre a semana com cobertura colaborativa, registros de campo e reuniao de pauta aberta.',
                'author': created_users['comunica.mst'],
                'is_pinned': False,
            },
            {
                'title': 'Plantio coletivo do sabado',
                'body': 'A Brigada Campo Vivo organiza acolhida, ferramentas e lanche solidario para o plantio coletivo do fim de semana.',
                'author': created_users['brigada.campo'],
                'community': created_users['brigada.campo'],
                'is_pinned': False,
            },
        ]

        for entry in notices_data:
            defaults = entry.copy()
            title = defaults.pop('title')
            CommunityNotice.objects.get_or_create(title=title, defaults=defaults)

        activities_data = [
            {
                'title': 'Plenaria geral da juventude',
                'description': 'Planejamento politico, informes do mes e definicao das brigadas da semana.',
                'activity_date': week_start + timedelta(days=1),
                'start_time': time(19, 0),
                'location': 'Sala comum da comunidade',
                'created_by': created_users['coord.juventude'],
            },
            {
                'title': 'Oficina de comunicacao popular',
                'description': 'Capacitacao pratica de texto, foto e video para fortalecer os avisos da comunidade.',
                'activity_date': week_start + timedelta(days=3),
                'start_time': time(14, 0),
                'location': 'Laboratorio de midia',
                'community': created_users['comunica.mst'],
                'created_by': created_users['comunica.mst'],
            },
            {
                'title': 'Mutirao agroecologico',
                'description': 'Manejo de canteiros, compostagem e organizacao dos insumos do grupo.',
                'activity_date': week_start + timedelta(days=5),
                'start_time': time(8, 30),
                'location': 'Assentamento Terra Livre',
                'community': created_users['brigada.campo'],
                'created_by': created_users['brigada.campo'],
            },
            {
                'title': 'Circulo de estudo e acolhida',
                'description': 'Troca de leituras, escuta da base e montagem do calendario do proximo mes.',
                'activity_date': week_start + timedelta(days=10),
                'start_time': time(18, 0),
                'location': 'Biblioteca comunitaria',
                'created_by': created_users['maria.raiz'],
            },
        ]

        for entry in activities_data:
            defaults = entry.copy()
            title = defaults.pop('title')
            activity_date = defaults.pop('activity_date')
            GroupActivity.objects.get_or_create(
                title=title,
                activity_date=activity_date,
                defaults=defaults,
            )

        tasks_data = [
            {
                'assignee': created_users['coord.juventude'],
                'title': 'Fechar a pauta da plenaria semanal',
                'description': 'Consolidar informes, pautas urgentes e confirmacoes das brigadas.',
                'due_date': week_start + timedelta(days=2),
                'status': WeeklyTask.Status.IN_PROGRESS,
                'created_by': created_users['coord.juventude'],
            },
            {
                'assignee': created_users['brigada.campo'],
                'title': 'Separar ferramentas do mutirao',
                'description': 'Revisar enxadas, sementes, agua e equipes de apoio para o plantio coletivo.',
                'due_date': week_start + timedelta(days=4),
                'status': WeeklyTask.Status.PENDING,
                'created_by': created_users['coord.juventude'],
            },
            {
                'assignee': created_users['comunica.mst'],
                'title': 'Publicar card e chamada da jornada cultural',
                'description': 'Subir arte, texto-base e lembrete nos canais internos da rede.',
                'due_date': week_start + timedelta(days=3),
                'status': WeeklyTask.Status.IN_PROGRESS,
                'created_by': created_users['coord.juventude'],
            },
            {
                'assignee': created_users['maria.raiz'],
                'title': 'Confirmar presenca da turma do circulo',
                'description': 'Passar nas mensagens da semana e fechar a lista da atividade de sexta.',
                'due_date': week_start + timedelta(days=5),
                'status': WeeklyTask.Status.PENDING,
                'created_by': created_users['comunica.mst'],
            },
        ]

        for entry in tasks_data:
            defaults = entry.copy()
            assignee = defaults.pop('assignee')
            title = defaults.pop('title')
            WeeklyTask.objects.get_or_create(
                assignee=assignee,
                title=title,
                due_date=defaults['due_date'],
                defaults=defaults,
            )

        health_unit, _ = HealthUnit.objects.update_or_create(
            name='Unidade de Saude Popular',
            defaults={
                'location': 'Nucleo central da comunidade',
                'phone_number': '+55 81 3333-2026',
                'description': 'Acolhimento, consultas basicas, organizacao de agendamentos e acompanhamento de saude da base.',
                'lead_operator': created_users['saude.unidade'],
                'is_active': True,
            },
        )

        HealthRecord.objects.update_or_create(
            patient=created_users['maria.raiz'],
            unit=health_unit,
            defaults={
                'blood_type': 'O+',
                'allergies': 'Poeira e picada de inseto.',
                'chronic_conditions': 'Nenhuma condicao cronica registrada.',
                'medications_in_use': 'Vitamina C quando orientado.',
                'emergency_contact_name': 'Luzia da Raiz',
                'emergency_contact_phone': '+55 85 98888-2001',
                'care_notes': 'Acompanhar alimentacao e hidratacao durante as jornadas longas.',
                'updated_by': created_users['saude.unidade'],
            },
        )
        HealthRecord.objects.update_or_create(
            patient=created_users['comunica.mst'],
            unit=health_unit,
            defaults={
                'blood_type': 'A+',
                'allergies': 'Sem alergias relatadas.',
                'chronic_conditions': 'Tensao muscular em epocas de cobertura intensa.',
                'medications_in_use': 'Analgesico leve quando prescrito.',
                'emergency_contact_name': 'Equipe de comunicacao',
                'emergency_contact_phone': '+55 81 97777-3030',
                'care_notes': 'Priorizar pausas e ergonomia em coberturas prolongadas.',
                'updated_by': created_users['saude.unidade'],
            },
        )

        future_slot = timezone.now() + timedelta(days=2)
        future_slot = future_slot.replace(hour=9, minute=30, second=0, microsecond=0)
        appointment, _ = HealthAppointment.objects.update_or_create(
            patient=created_users['maria.raiz'],
            unit=health_unit,
            scheduled_for=future_slot,
            defaults={
                'assigned_operator': created_users['saude.unidade'],
                'created_by': created_users['coord.juventude'],
                'appointment_type': HealthAppointment.AppointmentType.CONSULTATION,
                'status': HealthAppointment.Status.CONFIRMED,
                'reason': 'Consulta de acompanhamento da semana',
                'notes': 'Levar anotacoes de sono, hidratacao e rotina dos estudos.',
            },
        )

        consultation_time = timezone.now() - timedelta(days=2)
        consultation_time = consultation_time.replace(hour=15, minute=0, second=0, microsecond=0)
        completed_appointment, _ = HealthAppointment.objects.update_or_create(
            patient=created_users['comunica.mst'],
            unit=health_unit,
            scheduled_for=consultation_time,
            defaults={
                'assigned_operator': created_users['saude.unidade'],
                'created_by': created_users['coord.juventude'],
                'appointment_type': HealthAppointment.AppointmentType.FOLLOW_UP,
                'status': HealthAppointment.Status.COMPLETED,
                'reason': 'Retorno apos jornada de comunicacao',
                'notes': 'Avaliar cansaco e intensidade de trabalho.',
            },
        )
        HealthConsultation.objects.update_or_create(
            appointment=completed_appointment,
            defaults={
                'patient': created_users['comunica.mst'],
                'unit': health_unit,
                'operator': created_users['saude.unidade'],
                'consultation_date': consultation_time,
                'symptoms': 'Cansaco, tensao nos ombros e dor de cabeca leve.',
                'evaluation_notes': 'Sem sinais de gravidade. Quadro compativel com sobrecarga e poucas pausas.',
                'procedures': 'Escuta clinica, orientacao postural e afericao de sinais basicos.',
                'guidance': 'Descanso, alongamento, agua frequente e pausa entre coberturas.',
                'referral_notes': '',
                'follow_up_date': timezone.localdate() + timedelta(days=10),
            },
        )

        artwork, _ = Artwork.objects.update_or_create(
            inventory_number='QD-001',
            defaults={
                'name': 'Memoria da Colheita',
                'author': 'Maria Aparecida',
                'storage_location': 'Reserva tecnica / Estante A',
                'condition_notes': 'Conservar longe de umidade.',
                'notes': 'Pintura em tela cadastrada como exemplo do acervo.',
                'created_by': created_users['almox.enff'],
                'is_active': True,
            },
        )
        ArtworkMovement.objects.get_or_create(
            artwork=artwork,
            movement_type=ArtworkMovement.MovementType.CHECK_OUT,
            movement_date=timezone.localdate(),
            taken_by='Joana Silva',
            defaults={
                'phone_number': '(11) 99999-0000',
                'class_group': 'Oficina de artes',
                'cpp_responsible': 'CPP Maria',
                'operator_name': created_users['almox.enff'].display_name,
                'due_date': timezone.localdate() + timedelta(days=7),
                'notes': 'Saiu para atividade pedagogica do acervo.',
                'created_by': created_users['almox.enff'],
            },
        )
        WarehouseActivity.objects.get_or_create(
            artwork=artwork,
            activity_date=timezone.localdate(),
            activity_type=WarehouseActivity.ActivityType.EXHIBITION,
            defaults={
                'responsible': 'Coordenacao pedagogica',
                'status': WarehouseActivity.Status.CONFIRMED,
                'notes': 'Exposicao interna com turma da escola.',
                'created_by': created_users['almox.enff'],
            },
        )
        WarehouseFollowUp.objects.get_or_create(
            artwork=artwork,
            followup_date=timezone.localdate(),
            responsible='Operadora do Almoxarifado',
            defaults={
                'reason': 'Conferencia de conservacao da obra.',
                'action_taken': 'Registro visual e checagem do local de armazenamento.',
                'status': WarehouseFollowUp.Status.OPEN,
                'destination': 'Reserva tecnica',
                'created_by': created_users['almox.enff'],
            },
        )
        WarehouseStockItem.objects.update_or_create(
            material='Papel A4',
            batch='PM-08',
            defaults={
                'item_class': 'Secretaria',
                'unit': WarehouseStockItem.Unit.BOXES,
                'quantity': 14,
                'minimum_quantity': 6,
                'expiry_date': timezone.localdate() + timedelta(days=180),
                'location': 'Armario C / Gaveta 1',
                'notes': 'Material usado para catalogacao e fichas do acervo.',
                'created_by': created_users['almox.enff'],
            },
        )

        self.stdout.write(self.style.SUCCESS('Bootstrap concluido com sucesso.'))
        self.stdout.write(self.style.WARNING(f'Senha demo para todos os perfis: {DEMO_PASSWORD}'))
        self.stdout.write('Perfis: coord.juventude, brigada.campo, comunica.mst, maria.raiz, saude.unidade, almox.enff')
