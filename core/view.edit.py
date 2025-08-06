# -*- coding: utf-8 -*-
"""
Created on Tue Aug  5 23:20:27 2025

@author: Home
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json, urllib.request, os
from django.utils import timezone
from .models import UserDefinedVariable ,AlgoList, AlgorithmLogic, Broker, AlgoRegister, AlgoStatus, InstrumentList, Condition,TechnicalIndicator,Variable, VariableParameter
from .forms import CustomUserCreationForm, AlgorithmForm
from django.core.serializers.json import DjangoJSONEncoder
from core.utils.condition_utils import save_condition_structure,serialize_conditions
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.safestring import mark_safe
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict


# ---------- Signup ----------
def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.name = form.cleaned_data['name']
            user.email = form.cleaned_data['email']
            user.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


# ---------- Instruments Setup ----------
instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

def fetch_instruments():
    response = urllib.request.urlopen(instrument_url)
    instruments = json.loads(response.read())
    instrument_dict = {}
    for inst in instruments:
        instrument_dict.setdefault(inst['name'], set()).add(inst['expiry'])
    return [{'name': k, 'expiry': list(v)} for k, v in instrument_dict.items()]

def fetch_instruments_grouped():
    instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    response = urllib.request.urlopen(instrument_url)
    instruments = json.loads(response.read())

    instrument_dict = {}
    for inst in instruments:
        name = inst['name']
        expiry = inst['expiry']
        if name not in instrument_dict:
            instrument_dict[name] = set()
        instrument_dict[name].add(expiry)

    grouped_instruments = []
    for name, expiries in instrument_dict.items():
        grouped_instruments.append({
            'name': name,
            'expiries': sorted(list(expiries))  # 'expiries' instead of 'expiry'
        })

    return grouped_instruments

def get_grouped_instruments(request):
    grouped_data = fetch_instruments_grouped()
    return JsonResponse(grouped_data, safe=False)

def get_instruments():
    file_path = 'instruments.json'
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    data = fetch_instruments()
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
    return data


@csrf_exempt
@require_POST
@login_required
def save_user_variable(request):
    try:
        data = json.loads(request.body)
        name = data.get("name")
        expression = data.get("expression")
        user = request.user

        if not name or not isinstance(expression, list):
            return JsonResponse({'error': 'Invalid data'}, status=400)

        # Update if exists
        obj, created = UserDefinedVariable.objects.update_or_create(
            user=user,
            name=name,
            defaults={'expression': expression}
        )
        return JsonResponse({'status': 'ok', 'updated': not created})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_POST
@login_required
def delete_user_variable(request):
    try:
        data = json.loads(request.body)
        name = data.get("name")
        if name:
            UserDefinedVariable.objects.filter(name=name, user=request.user).delete()
            return JsonResponse({"status": "success"})
        return JsonResponse({"status": "error", "message": "Name required"}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
def check_algo_name(request):
    name = request.GET.get("name", "").strip()
    if not name:
        return JsonResponse({"valid": False, "message": "Name cannot be empty."})

    exists = AlgoList.objects.filter(algo_name=name, created_by=request.user).exists()
    if exists:
        return JsonResponse({"valid": False, "message": "This algorithm name already exists."})
    
    return JsonResponse({"valid": True})

@require_http_methods(["POST"])
@staff_member_required  # 👈 restrict to staff/admin users only
def insert_instruments(request):
    InstrumentList.objects.all().delete()
    response = urllib.request.urlopen(instrument_url)
    instruments = json.loads(response.read())
    instruments = [item for item in instruments if item["instrumenttype"] == "OPTSTK"]
    for inst in instruments:
        InstrumentList.objects.create(
            token=inst['token'], symbol=inst['symbol'], name=inst['name'],
            expiry=inst['expiry'], strike=inst['strike'], lotsize=inst['lotsize'],
            instrumenttype=inst['instrumenttype'], exch_seg=inst['exch_seg'],
            tick_size=inst['tick_size']
        )
    return JsonResponse({'message': 'Instruments inserted successfully'})


# ---------- Dashboard ----------
@login_required
def profile(request):
    user_algos = AlgoRegister.objects.filter(user=request.user)
    return render(request, 'core/profile.html', {'name': request.user.username, 'algo_registers': user_algos})


# ---------- Broker ----------
@require_http_methods(["GET", "POST"])
def add_broker(request):
    if request.method == 'POST':
        data = request.POST
        Broker.objects.create(
            broker_name=data['BrokerName'],
            root_api=data['RootAPI'],
            server_ip=data.get('ServerIP'),
            password_req=data.get('PasswordReq'),
            authenticator_req=data.get('AuthenticatorReq')
        )
        return redirect('profile')
    return render(request, 'createlist/add_broker.html')


@login_required
@require_http_methods(["GET", "POST"])
def add_algo(request):
    if request.method == "POST":
        name = request.POST.get("AlgoName")
        fund = request.POST.get("Minimum_Fund_Reqd")
        desc = request.POST.get("Algo_description")
        order_direction = request.POST.get("order_direction")  # Buy/Sell
        order_type = request.POST.get("order_type")            # Market/Limit/LimitThenMarket

        algo = AlgoList.objects.create(
            algo_name=name,
            minimum_fund_reqd=fund,
            algo_description=desc,
            created_by=request.user,
            created_at=timezone.now(),
            updated_at=timezone.now()
        )
        # Save user-defined variables
        for key in request.POST:
            if key.startswith("user_variable_json_"):
                try:
                    raw_json = request.POST[key]
                    var_data = json.loads(raw_json)
                    var_name = var_data.get("name")
                    var_expr = var_data.get("expression")

                    if var_name and isinstance(var_expr, list):
                # Avoid duplicates
                        if not UserDefinedVariable.objects.filter(algo=algo, user=request.user, name=var_name).exists():
                            UserDefinedVariable.objects.create(
                                algo=algo,
                                user=request.user,
                                name=var_name,
                                expression=var_expr
                                )
                except json.JSONDecodeError as e:
                    print(f"[UserVariable Error] {key}: {e}")

        instruments = request.POST.getlist("instrument_name[]")
        
        expiries = request.POST.getlist("expiry_date[]")
        strikes = request.POST.getlist("strike_price[]")
        order_directions = request.POST.getlist("order_direction[]")
        order_types = request.POST.getlist("order_type[]")
        option_types = request.POST.getlist("option_type[]")
        for i in range(len(instruments)):
            logic = AlgorithmLogic.objects.create(
                algo=algo,
                num_stocks=i + 1,
                instrument_name=instruments[i],
                expiry_date=expiries[i],
                strike_price=strikes[i],
                option_type=option_types[i],          # ✅
                order_direction=order_directions[i],  # ✅
                order_type=order_types[i]
            )

            # Entry conditions
            try:
                entry_json = request.POST.get(f"entry_conditions_json_{i}", "[]")
                entry_data = json.loads(entry_json)
                save_condition_structure(logic, entry_data, condition_type="entry")
            except json.JSONDecodeError as e:
                print(f"[Entry Condition Error] Leg {i+1}: {e}")

            # Exit conditions
            try:
                exit_json = request.POST.get(f"exit_conditions_json_{i}", "[]")
                exit_data = json.loads(exit_json)
                save_condition_structure(logic, exit_data, condition_type="exit")
            except json.JSONDecodeError as e:
                print(f"[Exit Condition Error] Leg {i+1}: {e}")

        messages.success(request, "✅ Algorithm created successfully")
        return redirect("algo_list")
    

    # GET method
    instruments = InstrumentList.objects.all()

    grouped = {}
    all_symbols = [] 
    for inst in instruments:
        name = inst.name
        symbol = inst.symbol
        all_symbols.append(symbol)
        if name not in grouped:
            grouped[name] = {"expiries": set(), "strikes": set()}
        if inst.expiry:
            grouped[name]["expiries"].add(inst.expiry)
        if inst.strike:
            grouped[name]["strikes"].add(inst.strike)

    instruments_json = [
        {
            "name": k,
            "expiries": sorted(grouped[k]["expiries"]),
            "strikes": sorted(grouped[k]["strikes"])
        } for k in grouped
    ]
    symbol_list_json = json.dumps(sorted(set(all_symbols)))  # 🔁 For Select2 dropdowns

    variables = Variable.objects.prefetch_related('parameters').all()
    indicators_json = json.dumps([
        {
            'name': v.name,
            'display_name': v.display_name,
            'category': v.category.name if v.category else 'uncategorized',  # ✅ ADD THIS LINE
            'parameters': [
                {
                    'name': p.name,
                    'input_type': p.input_type,
                    'default_value': p.default_value,
                    'source_model': p.source_model,
                    'source_field': p.source_field,
                    'description': p.description,
                } for p in v.parameters.all()
                ]
        } for v in variables
    ], cls=DjangoJSONEncoder)
    
    #user_variables = UserDefinedVariable.objects.filter(user=request.user)
    user_variables = []
    user_vars_json = json.dumps([
        {"name": v.name, "expression": v.expression} for v in user_variables
    ], cls=DjangoJSONEncoder)

    return render(request, "algorelated/add_algo.html", {
        "instruments_json": instruments_json,
        "indicators_json": indicators_json,
        "symbol_list_json": symbol_list_json,
        "user_vars_json": mark_safe(user_vars_json)  # 👉 make it available in your template
    })

    
def save_condition_structure(algo_logic, conditions, condition_type='entry', parent=None):
    for cond in conditions:
        lhs = cond.get('lhs', {})
        rhs = cond.get('rhs', {})

        current = Condition.objects.create(
            algo_logic=algo_logic,
            condition_type=condition_type,
            lhs_variable=lhs.get('name'),
            lhs_parameters=lhs.get('parameters', {}),
            operator=cond.get('operator'),
            rhs_type=rhs.get('type'),
            rhs_value=rhs.get('value') if rhs.get('type') == 'value' else None,
            rhs_variable=rhs.get('name') if rhs.get('type') == 'variable' else None,
            rhs_parameters=rhs.get('parameters', {}) if rhs.get('type') == 'variable' else {},
            connector=cond.get('connector', 'AND'),
            nested_condition=parent
        )

        for child in cond.get('children', []):
            save_condition_structure(algo_logic, [child], condition_type, parent=current)


# ---------- Edit Algo ----------

@login_required
def edit_algo(request, id):
    algo = get_object_or_404(AlgoList, id=id)
    logic_entries = list(AlgorithmLogic.objects.filter(algo=algo))
    user_variables = list(UserDefinedVariable.objects.filter(algo=algo, user=request.user))

    if request.method == 'POST':
        # TODO: add logic to update algo, variables, conditions
        pass

    # Prepare instruments (same as add view)
    instruments = InstrumentList.objects.all()
    grouped = {}
    all_symbols = []
    for inst in instruments:
        name = inst.name
        symbol = inst.symbol
        all_symbols.append(symbol)
        if name not in grouped:
            grouped[name] = {"expiries": set(), "strikes": set()}
        if inst.expiry:
            grouped[name]["expiries"].add(inst.expiry)
        if inst.strike:
            grouped[name]["strikes"].add(inst.strike)

    instruments_json = [
        {
            "name": k,
            "expiries": sorted(grouped[k]["expiries"]),
            "strikes": sorted(grouped[k]["strikes"])
        } for k in grouped
    ]
    symbol_list_json = json.dumps(sorted(set(all_symbols)))

    # Technical indicators
    variables = Variable.objects.prefetch_related('parameters').all()
    indicators_json = json.dumps([
        {
            'name': v.name,
            'display_name': v.display_name,
            'category': v.category.name if v.category else 'uncategorized',
            'parameters': [
                {
                    'name': p.name,
                    'input_type': p.input_type,
                    'default_value': p.default_value,
                    'source_model': p.source_model,
                    'source_field': p.source_field,
                    'description': p.description,
                } for p in v.parameters.all()
            ]
        } for v in variables
    ], cls=DjangoJSONEncoder)

    # Serialize user-defined variables
    user_vars_json = json.dumps([
        {"name": v.name, "expression": v.expression} for v in user_variables
    ], cls=DjangoJSONEncoder)

    # Serialize existing conditions
    legs_data = []
    for leg in logic_entries:
        legs_data.append({
            "num_stocks": leg.num_stocks,
            "instrument_name": leg.instrument_name,
            "expiry_date": leg.expiry_date,
            "strike_price": leg.strike_price,
            "option_type": leg.option_type,
            "order_type": leg.order_type,
            "entry_conditions": serialize_conditions(leg, "entry"),
            "exit_conditions": serialize_conditions(leg, "exit"),
        })

    return render(request, "algorelated/add_algo.html", {
        "algo": algo,
        "is_edit_mode": True,
        "instruments_json": instruments_json,
        "symbol_list_json": symbol_list_json,
        "indicators_json": indicators_json,
        "user_vars_json": [
        {"name": v.name, "expression": v.expression} for v in user_variables
    ],
        "legs_json": legs_data,
        "editing":True
    })

#--------Algo list-------#
def algo_list(request):
    algos = AlgoList.objects.all()
    return render(request, 'algorelated/algo_list.html', {'algos': algos})
#--------Algo Delete----#
def delete_algo(request, id):
    algo = get_object_or_404(AlgoList, id=id)
    algo.delete()
    return redirect('algo_list')
# ---------- Algo Registration ----------
@require_http_methods(["POST"])
@login_required
def register_algo(request):
    algo_logic = get_object_or_404(AlgorithmLogic, pk=request.POST['AlgorithmLogicID'])
    broker = get_object_or_404(Broker, pk=request.POST['BrokerID'])
    reg = AlgoRegister.objects.create(
        user=request.user,
        algo=algo_logic,
        broker=broker,
        broker_username=request.POST['BrokerClientID'],
        api_key=request.POST.get('ClientAPIKey'),
        secret_key=request.POST.get('ClientSecretKey')
    )
    AlgoStatus.objects.create(algo_register=reg, status='registered')
    messages.success(request, 'Algorithm registered successfully!')
    return redirect('profile')


# ---------- Run Algo ----------
@require_http_methods(["POST"])
@login_required
def run_algo(request):
    algo_register = get_object_or_404(AlgoRegister, pk=request.POST['AlgoRegisterID'], user=request.user)
    status = get_object_or_404(AlgoStatus, algo_register=algo_register)
    status.status = 'run'
    status.lot_size = request.POST['SelectLotSize']
    status.save()
    return redirect('profile')
def get_minimum_fund(request):
    algo_id = request.GET.get('algo_id')
    try:
        algo = AlgoList.objects.get(id=algo_id)
        return JsonResponse({'minimum_fund': algo.minimum_fund})
    except AlgoList.DoesNotExist:
        return JsonResponse({'error': 'Algo not found'}, status=404)

# ---------- Extra ----------
def index(request):
    return render(request, 'core/index.html')


def build_algo(request):
    segments = InstrumentList.objects.values_list('exch_seg', flat=True).distinct()
    if request.method == 'POST':
        results = [f"Line {i+1}: {request.POST.get(f'line_{i+1}')}" for i in range(int(request.POST.get('line_count', 0))) if request.POST.get(f'line_{i+1}').strip()]
        return render(request, 'BuildAlgo.html', {'results': results, 'Segments': segments})
    return render(request, 'algorelated/BuildAlgo.html', {'Segments': segments})
