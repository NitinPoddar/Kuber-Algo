from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json, urllib.request, os
from django.utils import timezone
from .models import UserDefinedConstant,AlgoList, AlgorithmLogic, Broker, AlgoRegister, AlgoStatus, InstrumentList, Condition,TechnicalIndicator,Variable, VariableParameter
from .forms import CustomUserCreationForm, AlgorithmForm
from django.core.serializers.json import DjangoJSONEncoder
from core.utils.condition_utils import save_condition_structure
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.safestring import mark_safe
from django.core.serializers.json import DjangoJSONEncoder
 


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
        for key in request.POST:
            if key.startswith("user_constant_json_"):
                try:
                    raw_json = request.POST[key]
                    const_data = json.loads(raw_json)
                    name = const_data.get("name")
                    expression = const_data.get("expression")

                    if name and isinstance(expression, list):
                        UserDefinedConstant.objects.create(
                            algo=algo,
                            name=name,
                            expression=expression
                        )
                except json.JSONDecodeError as e:
                    print(f"[UserConstant Error] {key}: {e}")
        
        instruments = request.POST.getlist("instrument_name[]")
        
        expiries = request.POST.getlist("expiry_date[]")
        strikes = request.POST.getlist("strike_price[]")

        for i in range(len(instruments)):
            logic = AlgorithmLogic.objects.create(
                algo=algo,
                num_stocks=i + 1,
                instrument_name=instruments[i],
                expiry_date=expiries[i],
                strike_price=strikes[i],
                option_type=order_direction,   # Buy or Sell
                order_type=order_type          # Market/Limit/LimitThenMarket
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
    

    return render(request, "algorelated/add_algo.html", {
        "instruments_json": instruments_json,
        "indicators_json": indicators_json,
        "symbol_list_json":symbol_list_json
    })

def save_condition_structure(algo_logic, conditions, condition_type='entry', parent=None):
    for cond in conditions:
        current = Condition.objects.create(
            algo_logic=algo_logic,
            condition_type=condition_type,
            variable_name=cond.get('variable_name'),
            operator=cond.get('operator'),
            value=str(cond.get('value')),
            nested_condition=parent
        )
        for child in cond.get('children', []):
            save_condition_structure(algo_logic, [child], condition_type, parent=current)


# ---------- Edit Algo ----------
def edit_algo(request, id):
    algo = get_object_or_404(AlgoList, id=id)  # Correct model is AlgoList
    logic_entries = AlgorithmLogic.objects.filter(algo=algo)

    if request.method == 'POST':
        form = AlgorithmForm(request.POST, instance=algo)
        if form.is_valid():
            form.save()

            # Delete old logic rows
            AlgorithmLogic.objects.filter(algo=algo).delete()
            logic_count = len(request.POST.getlist('instrument_name[]'))

            for i in range(logic_count):
                AlgorithmLogic.objects.create(
                    algo=algo,
                    instrument_name=request.POST.getlist('instrument_name[]')[i],
                    expiry_date=request.POST.getlist('expiry_date[]')[i],
                    strike_price=request.POST.getlist('strike_price[]')[i],
                    option_type=request.POST.getlist('option_type[]')[i],
                    order_type=request.POST.getlist('order_type[]')[i],
                    entry_condition=request.POST.getlist('entry_condition[]')[i],
                    exit_condition=request.POST.getlist('exit_condition[]')[i]
                )
            return redirect('algo_list')
    else:
        form = AlgorithmForm(instance=algo)

    field_names = [
        "instrument_name", "expiry_date", "strike_price",
        "option_type", "order_type", "entry_condition", "exit_condition"
    ]

    return render(request, 'algorelated/edit_algo.html', {
        'form': form,
        'logic_entries': logic_entries,
        'field_names': field_names,
        'algo': algo
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
