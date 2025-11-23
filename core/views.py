from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import random
from datetime import date, time, datetime
from django.utils import timezone
from decimal import Decimal

from .forms import RegisterForm, DepositForm, WithdrawalForm, BankDetailsForm
from .models import PlatformSettings, CustomUser, Level, UserLevel, BankDetails, Deposit, Withdrawal, Task, PlatformBankDetails, Roulette, RouletteSettings

# --- FUNÇÃO ATUALIZADA ---
def home(request):
    if request.user.is_authenticated:
        return redirect('menu')
    else:
        return redirect('cadastro')
# --- FIM DA FUNÇÃO ATUALIZADA ---

# ==================================================================================
# FUNÇÃO MENU - ATUALIZADA PARA INCLUIR TODOS OS INDICADORES DE RENDA
# ==================================================================================
@login_required
def menu(request):
    user = request.user
    
    # Busca o nível ativo
    active_level = UserLevel.objects.filter(user=user, is_active=True).first()

    # Calcula Depósito Activo (Aprovado)
    approved_deposit_total = Deposit.objects.filter(user=user, is_approved=True).aggregate(Sum('amount'))['amount__sum'] or 0

    # Calcula Renda de Hoje (Tarefas concluídas hoje)
    today = date.today()
    daily_income = Task.objects.filter(user=user, completed_at__date=today).aggregate(Sum('earnings'))['earnings__sum'] or 0

    # Calcula Total Sacado (Aprovado - Usando a lógica da função 'renda')
    total_withdrawals = Withdrawal.objects.filter(user=user, status='Aprovado').aggregate(Sum('amount'))['amount__sum'] or 0

    # Busca link do WhatsApp
    try:
        platform_settings = PlatformSettings.objects.first()
        whatsapp_link = platform_settings.whatsapp_link
    except (PlatformSettings.DoesNotExist, AttributeError):
        whatsapp_link = '#'

    context = {
        'user': user, # Necessário para Saldo Activo (user.available_balance) e Subsídio (user.subsidy_balance)
        'active_level': active_level,
        'approved_deposit_total': approved_deposit_total,
        'daily_income': daily_income,
        'total_withdrawals': total_withdrawals,
        'whatsapp_link': whatsapp_link,
    }
    return render(request, 'menu.html', context)
# ==================================================================================

def cadastro(request):
    invite_code_from_url = request.GET.get('invite', None)

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            
            # --- Lógica 1: Saldo Inicial (1000 KZ) no Cadastro ---
            user.available_balance = 1000 # Define o saldo inicial de 1000 KZ
            # --- Fim da Lógica 1 ---
            
            # --- CORREÇÃO AQUI: O NOME DO CAMPO NO FORM É 'invited_by_code' ---
            invited_by_code = form.cleaned_data.get('invited_by_code')
            
            if invited_by_code:
                try:
                    invited_by_user = CustomUser.objects.get(invite_code=invited_by_code)
                    user.invited_by = invited_by_user
                except CustomUser.DoesNotExist:
                    messages.error(request, 'Código de convite inválido.')
                    return render(request, 'cadastro.html', {'form': form})
            
            user.save()
            login(request, user)
            messages.success(request, 'Cadastro realizado com sucesso! Você recebeu 1000 KZ de saldo inicial.')
            return redirect('menu')
        else:
            try:
                whatsapp_link = PlatformSettings.objects.first().whatsapp_link
            except (PlatformSettings.DoesNotExist, AttributeError):
                whatsapp_link = '#'
            return render(request, 'cadastro.html', {'form': form, 'whatsapp_link': whatsapp_link})
    else:
        # --- CORREÇÃO AQUI: O NOME DO CAMPO NO FORM É 'invited_by_code' ---
        if invite_code_from_url:
            form = RegisterForm(initial={'invited_by_code': invite_code_from_url})
        else:
            form = RegisterForm()
    
    try:
        whatsapp_link = PlatformSettings.objects.first().whatsapp_link
    except (PlatformSettings.DoesNotExist, AttributeError):
        whatsapp_link = '#'

    return render(request, 'cadastro.html', {'form': form, 'whatsapp_link': whatsapp_link})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            authenticate(request, user)
            login(request, user)
            return redirect('menu')
    else:
        form = AuthenticationForm()

    try:
        whatsapp_link = PlatformSettings.objects.first().whatsapp_link
    except (PlatformSettings.DoesNotExist, AttributeError):
        whatsapp_link = '#'

    return render(request, 'login.html', {'form': form, 'whatsapp_link': whatsapp_link})

@login_required
def user_logout(request):
    logout(request)
    return redirect('menu')

# --- FUNÇÃO DE DEPÓSITO ATUALIZADA PARA O NOVO FLUXO ---
@login_required
def deposito(request):
    platform_bank_details = PlatformBankDetails.objects.all()
    deposit_instruction = PlatformSettings.objects.first().deposit_instruction if PlatformSettings.objects.first() else 'Instruções de depósito não disponíveis.'
    
    # Busca todos os valores de depósito dos Níveis para a Etapa 2
    level_deposits = Level.objects.all().values_list('deposit_value', flat=True).distinct().order_by('deposit_value')
    # Converte os Decimais para strings formatadas para JS
    level_deposits_list = [str(d) for d in level_deposits] 

    if request.method == 'POST':
        # O formulário agora é submetido na Etapa 3
        # Os campos 'amount' e 'proof_of_payment' são necessários
        form = DepositForm(request.POST, request.FILES)
        if form.is_valid():
            deposit = form.save(commit=False)
            deposit.user = request.user
            deposit.save()
            
            # Não exibe mensagem aqui, mas sim no template
            # O template irá exibir uma tela de sucesso após a submissão
            return render(request, 'deposito.html', {
                'platform_bank_details': platform_bank_details,
                'deposit_instruction': deposit_instruction,
                'level_deposits_list': level_deposits_list,
                'deposit_success': True # Variável de contexto para a tela de sucesso
            })
        else:
            messages.error(request, 'Erro ao enviar o depósito. Verifique o valor e o comprovativo.')
    
    # Se não for POST ou se for a primeira vez acessando a página
    form = DepositForm()
    
    context = {
        'platform_bank_details': platform_bank_details,
        'deposit_instruction': deposit_instruction,
        'form': form,
        'level_deposits_list': level_deposits_list,
        'deposit_success': False, # Estado inicial
    }
    return render(request, 'deposito.html', context)
# --- FIM DA FUNÇÃO DE DEPÓSITO ATUALIZADA ---

@login_required
def approve_deposit(request, deposit_id):
    if not request.user.is_staff:
        messages.error(request, 'Você não tem permissão para realizar esta ação.')
        return redirect('menu')

    deposit = get_object_or_404(Deposit, id=deposit_id)
    if not deposit.is_approved:
        deposit.is_approved = True
        deposit.save()
        
        deposit.user.available_balance += deposit.amount
        deposit.user.save()
        
        # --- LÓGICA DE COMISSÃO DE 15% REMOVIDA DAQUI ---
        # A comissão será aplicada na compra do nível (`nivel`)
        
        messages.success(request, f'Depósito de {deposit.amount} KZ aprovado para {deposit.user.phone_number}. Saldo atualizado.')
    
    return redirect('renda')

# ==================================================================================
# FUNÇÃO SAQUE - ATUALIZADA PARA HORÁRIO, VALOR MÍNIMO E LIMITE DIÁRIO
# ==================================================================================
@login_required
def saque(request):
    # Valores de restrição conforme solicitado
    MIN_WITHDRAWAL_AMOUNT = 2500
    START_TIME = time(9, 0, 0) # 09:00:00 (Hora de Luanda, Angola)
    END_TIME = time(17, 0, 0) # 17:00:00 (Hora de Luanda, Angola)

    withdrawal_instruction = PlatformSettings.objects.first().withdrawal_instruction if PlatformSettings.objects.first() else 'Instruções de saque não disponíveis.'
    
    withdrawal_records = Withdrawal.objects.filter(user=request.user).order_by('-created_at')
    
    has_bank_details = BankDetails.objects.filter(user=request.user).exists()
    
    # Verifica o horário e data atual locais (IMPORTANTE PARA A CONSISTÊNCIA)
    now = timezone.localtime(timezone.now()).time()
    today = timezone.localdate(timezone.now())
    is_time_to_withdraw = START_TIME <= now <= END_TIME
    
    # ✅ NOVO FILTRO CORRIGIDO: Checa se já existe um pedido de saque (Pendente ou Aprovado) hoje
    withdrawals_today_count = Withdrawal.objects.filter(
        user=request.user,
        created_at__date=today, # Filtra apenas pela data de criação
        status__in=['Pendente', 'Aprovado']
    ).count()

    can_withdraw_today = withdrawals_today_count == 0
    
    if request.method == 'POST':
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            
            # 1. Checa o limite diário de saque
            if not can_withdraw_today:
                messages.error(request, 'Você já solicitou um saque hoje. É permitido apenas **1 saque por dia**.')
                return redirect('saque')

            # 2. Checa o horário de saque
            if not is_time_to_withdraw:
                messages.error(request, f'O horário de saque é das {START_TIME.strftime("%H:%M")}h até as {END_TIME.strftime("%H:%M")}h (Hora de Luanda). Tente novamente mais tarde.')
                return redirect('saque')

            # 3. Checa as coordenadas bancárias
            if not has_bank_details:
                messages.error(request, 'Por favor, adicione suas coordenadas bancárias no seu perfil antes de solicitar um saque.')
                return redirect('perfil')
            
            # 4. Checa o valor mínimo
            if amount < MIN_WITHDRAWAL_AMOUNT:
                messages.error(request, f'O valor mínimo para saque é {MIN_WITHDRAWAL_AMOUNT:.2f} KZ.')
            # 5. Checa o saldo
            elif request.user.available_balance < amount:
                messages.error(request, 'Saldo insuficiente.')
            else:
                # Se tudo estiver ok
                withdrawal = Withdrawal.objects.create(user=request.user, amount=amount)
                request.user.available_balance -= amount
                request.user.save()
                messages.success(request, 'Saque solicitado com sucesso. Aguarde a aprovação. Você só poderá solicitar um novo saque amanhã.')
                return redirect('saque')
    else:
        form = WithdrawalForm()

    context = {
        'withdrawal_instruction': withdrawal_instruction,
        'withdrawal_records': withdrawal_records,
        'form': form,
        'has_bank_details': has_bank_details,
        'is_time_to_withdraw': is_time_to_withdraw,
        'MIN_WITHDRAWAL_AMOUNT': MIN_WITHDRAWAL_AMOUNT,
        'can_withdraw_today': can_withdraw_today, # Passa a informação para o template
    }
    return render(request, 'saque.html', context)
# ==================================================================================

@login_required
def tarefa(request):
    user = request.user
    
    # Encontra o nível ativo do usuário
    active_level = UserLevel.objects.filter(user=user, is_active=True).first()
    has_active_level = active_level is not None
    
    # Define o número de tarefas
    max_tasks = 1
    tasks_completed_today = 0
    
    if has_active_level:
        today = date.today()
        tasks_completed_today = Task.objects.filter(user=user, completed_at__date=today).count()
    
    context = {
        'has_active_level': has_active_level,
        'active_level': active_level,
        'tasks_completed_today': tasks_completed_today,
        'max_tasks': max_tasks,
    }
    return render(request, 'tarefa.html', context)

@login_required
@require_POST
def process_task(request):
    user = request.user
    active_level = UserLevel.objects.filter(user=user, is_active=True).first()

    if not active_level:
        return JsonResponse({'success': False, 'message': 'Você não tem um nível ativo para realizar tarefas.'})

    today = date.today()
    tasks_completed_today = Task.objects.filter(user=user, completed_at__date=today).count()
    max_tasks = 1

    if tasks_completed_today >= max_tasks:
        return JsonResponse({'success': False, 'message': 'Você já concluiu todas as tarefas diárias.'})

    earnings = active_level.level.daily_gain
    Task.objects.create(user=user, earnings=earnings)
    user.available_balance += earnings
    user.save()

    # --- Lógica 2: Subsídio de 100 KZ para o Patrocinador por Tarefa do Subordinado ---
    invited_by_user = user.invited_by
    if invited_by_user:
        # Verifica se o patrocinador tem pelo menos um nível ativo para receber o subsídio
        if UserLevel.objects.filter(user=invited_by_user, is_active=True).exists():
            subsidy_amount = Decimal('100.00')
            
            # Adiciona o subsídio ao saldo e subsídio do patrocinador
            invited_by_user.available_balance += subsidy_amount
            invited_by_user.subsidy_balance += subsidy_amount
            invited_by_user.save()
            
            # Nota: Não usamos messages aqui pois é uma função JsonResponse
            # O subsídio é dado de forma silenciosa para o patrocinador
            # (Você pode implementar um sistema de notificação em outro lugar se quiser)
    # --- Fim da Lógica 2 ---

    return JsonResponse({'success': True, 'daily_gain': earnings})

@login_required
def nivel(request):
    levels = Level.objects.all().order_by('deposit_value')
    user_levels = UserLevel.objects.filter(user=request.user, is_active=True).values_list('level__id', flat=True)
    
    if request.method == 'POST':
        level_id = request.POST.get('level_id')
        level_to_buy = get_object_or_404(Level, id=level_id)

        if level_to_buy.id in user_levels:
            messages.error(request, 'Você já possui este nível.')
            return redirect('nivel')
        
        if request.user.available_balance >= level_to_buy.deposit_value:
            
            # --- LÓGICA DE SUBSÍDIO DE 15% NA COMPRA DO NÍVEL (Patrocinador) ---
            subordinate_user = request.user # O usuário que está comprando o nível (subordinado)
            invited_by_user = subordinate_user.invited_by # O patrocinador (quem o convidou)
            
            if invited_by_user:
                # 1. Verifica se o patrocinador tem pelo menos um nível ativo
                if UserLevel.objects.filter(user=invited_by_user, is_active=True).exists():
                    commission_rate = Decimal('0.15') # 15%
                    # 2. O cálculo é feito sobre o valor do nível comprado
                    commission_amount = level_to_buy.deposit_value * commission_rate 
                    
                    # 3. Adiciona a comissão ao saldo e subsídio do patrocinador
                    invited_by_user.available_balance += commission_amount
                    invited_by_user.subsidy_balance += commission_amount
                    invited_by_user.save()
                    
                    messages.success(request, f'🥳 Subsídio de {commission_amount:.2f} KZ concedido por {subordinate_user.phone_number} comprar o nível {level_to_buy.name}.')
                else:
                    messages.warning(request, 'Aviso: Seu patrocinador não recebeu comissão (Patrocinador sem nível ativo).')
            
            # ----------------------------------------------------------------------
            
            # Efetua a compra do nível
            request.user.available_balance -= level_to_buy.deposit_value
            UserLevel.objects.create(user=request.user, level=level_to_buy, is_active=True)
            request.user.level_active = True
            request.user.save()
            
            messages.success(request, f'Você comprou o nível {level_to_buy.name} com sucesso!')
        else:
            messages.error(request, 'Saldo insuficiente. Por favor, faça um depósito.')
        
        return redirect('nivel')
        
    context = {
        'levels': levels,
        'user_levels': user_levels,
    }
    return render(request, 'nivel.html', context)

@login_required
def equipa(request):
    user = request.user

    # 1. Encontra todos os membros da equipe (convidados diretos)
    team_members = CustomUser.objects.filter(invited_by=user).order_by('-date_joined')
    team_count = team_members.count()

    # 2. Obtém todos os Níveis disponíveis
    all_levels = Level.objects.all().order_by('deposit_value')

    # 3. Contabilização por Nível de Investimento
    levels_data = []
    total_investors = 0
    
    # Dicionário para armazenar membros por nível (para exibição no template)
    members_by_level = {} 
    
    # Preenche os dados para cada nível
    for level in all_levels:
        # Filtra membros da equipe que possuem este nível ATIVO
        members_with_level = team_members.filter(userlevel__level=level, userlevel__is_active=True).distinct()
        
        levels_data.append({
            'name': level.name,
            'count': members_with_level.count(),
            'members': members_with_level, 
        })
        members_by_level[level.name] = members_with_level
        total_investors += members_with_level.count()

    # 4. Contabilização de Não Investidores GERAL
    # Membros que NÃO têm NENHUM UserLevel ativo
    non_invested_members = team_members.exclude(userlevel__is_active=True)
    total_non_investors = non_invested_members.count()
    
    # Adiciona a contagem de não investidos na estrutura levels_data para a primeira aba
    levels_data.insert(0, {
        'name': 'Não Investido',
        'count': total_non_investors,
        'members': non_invested_members,
    })

    context = {
        'team_members': team_members, # Membros totais
        'team_count': team_count, # Contagem total de membros
        'invite_link': request.build_absolute_uri(reverse('cadastro')) + f'?invite={user.invite_code}',
        'levels_data': levels_data, # Dados detalhados por nível (para as abas)
        'total_investors': total_investors, # Contagem de investidores
        'total_non_investors': total_non_investors, # Contagem de não investidores
        'subsidy_balance': user.subsidy_balance, # Saldo de Subsídios
    }
    return render(request, 'equipa.html', context)

@login_required
def roleta(request):
    user = request.user
    
    context = {
        'roulette_spins': user.roulette_spins,
    }
    
    return render(request, 'roleta.html', context)

@login_required
@require_POST
def spin_roulette(request):
    user = request.user

    if not user.roulette_spins or user.roulette_spins <= 0:
        return JsonResponse({'success': False, 'message': 'Você não tem giros disponíveis para a roleta.'})

    user.roulette_spins -= 1
    user.save()
    
    try:
        roulette_settings = RouletteSettings.objects.first()
        
        if roulette_settings and roulette_settings.prizes:
            prizes_from_admin = [Decimal(p.strip()) for p in roulette_settings.prizes.split(',')]
            prizes_weighted = []
            for prize in prizes_from_admin:
                if prize <= 1000:
                    prizes_weighted.extend([prize] * 3)
                else:
                    prizes_weighted.append(prize)
            prize = random.choice(prizes_weighted)
        else:
            prizes = [Decimal('100'), Decimal('200'), Decimal('300'), Decimal('500'), Decimal('1000'), Decimal('2000')]
            prize = random.choice(prizes)

    except RouletteSettings.DoesNotExist:
        prizes = [Decimal('100'), Decimal('200'), Decimal('300'), Decimal('500'), Decimal('1000'), Decimal('2000')]
        prize = random.choice(prizes)

    Roulette.objects.create(user=user, prize=prize, is_approved=True)

    user.subsidy_balance += prize
    user.available_balance += prize
    user.save()

    return JsonResponse({'success': True, 'prize': prize, 'message': f'Parabéns! Você ganhou {prize} KZ.'})

@login_required
def sobre(request):
    try:
        platform_settings = PlatformSettings.objects.first()
        history_text = platform_settings.history_text if platform_settings else 'Histórico da plataforma não disponível.'
    except PlatformSettings.DoesNotExist:
        history_text = 'Histórico da plataforma não disponível.'

    return render(request, 'sobre.html', {'history_text': history_text})

@login_required
def perfil(request):
    bank_details, created = BankDetails.objects.get_or_create(user=request.user)
    user_levels = UserLevel.objects.filter(user=request.user, is_active=True)

    if request.method == 'POST':
        form = BankDetailsForm(request.POST, instance=bank_details)
        password_form = PasswordChangeForm(request.user, request.POST)

        if 'update_bank' in request.POST:
            if form.is_valid():
                form.save()
                messages.success(request, 'Detalhes bancários atualizados com sucesso!')
                return redirect('perfil')
            else:
                messages.error(request, 'Ocorreu um erro ao atualizar os detalhes bancários.')

        if 'change_password' in request.POST:
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Sua senha foi alterada com sucesso!')
                return redirect('perfil')
            else:
                messages.error(request, 'Ocorreu um erro ao alterar a senha. Verifique se a senha antiga está correta e a nova senha é válida.')
    else:
        form = BankDetailsForm(instance=bank_details)
        password_form = PasswordChangeForm(request.user)

    context = {
        'form': form,
        'password_form': password_form,
        'user_levels': user_levels,
    }
    return render(request, 'perfil.html', context)

@login_required
def renda(request):
    user = request.user
    
    active_level = UserLevel.objects.filter(user=user, is_active=True).first()

    approved_deposit_total = Deposit.objects.filter(user=user, is_approved=True).aggregate(Sum('amount'))['amount__sum'] or 0
    
    today = date.today()
    daily_income = Task.objects.filter(user=user, completed_at__date=today).aggregate(Sum('earnings'))['earnings__sum'] or 0

    # A linha abaixo foi alterada para corrigir o status para 'Aprovado'
    total_withdrawals = Withdrawal.objects.filter(user=user, status='Aprovado').aggregate(Sum('amount'))['amount__sum'] or 0

    total_income = (Task.objects.filter(user=user).aggregate(Sum('earnings'))['earnings__sum'] or 0) + user.subsidy_balance
    
    context = {
        'user': user,
        'active_level': active_level,
        'approved_deposit_total': approved_deposit_total,
        'daily_income': daily_income,
        'total_withdrawals': total_withdrawals,
        'total_income': total_income,
    }
    return render(request, 'renda.html', context)
    