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
import json, urllib.request, os,traceback
from django.utils import timezone
from .forms import CustomUserCreationForm, AlgorithmForm
from django.core.serializers.json import DjangoJSONEncoder
from core.utils.condition_utils import save_condition_structure,serialize_conditions
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.safestring import mark_safe
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from django.db.models import Q
from datetime import timedelta, date
from core.services.env_builder import build_env
from core.services.sandbox_exec import execute_user_code
from django.db.models import Sum
# views.py

from .models import (
    UserDefinedVariable ,
    AlgoList, 
    AlgorithmLogic, 
    Broker,  
    InstrumentList,
    Condition,
    TechnicalIndicator,
    Variable,
    VariableParameter,
    VariableCategory,
    BrokerAccount, 
    AlgoBrokerLink, 
    GlobalVariable, 
    AlgorithmLogic,AlgoRun,
    DailyPnl,
    ExecutionLog,
    AlgoStatusStyle
    )

# core/views.py
# views.py
# --- add these imports near the top ---
from django.utils.http import url_has_allowed_host_and_scheme

@login_required
@require_http_methods(["GET"])
def broker_account_create(request):
    next_url = request.GET.get("next") or "/dashboard/"
    if not url_has_allowed_host_and_scheme(next_url, {request.get_host()}, require_https=request.is_secure()):
        next_url = "/dashboard/"
    brokers = Broker.objects.all().order_by("broker_name")
    return render(request, "accounts/add_broker_account.html", {"brokers": brokers, "next": next_url})

# --- Register/link account to an algo card ---
@csrf_exempt
def api_dashboard_register(request, algo_id):
    """
    POST { "account_id": <id>, "role": "paper"|"primary"|"hedge", "is_default": bool }
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})
    user = request.user
    body = json.loads(request.body or "{}")
    account_id = body.get("account_id")
    role = body.get("role", "primary")
    is_default = bool(body.get("is_default", role != "paper"))

    if not account_id:
        return JsonResponse({"success": False, "error": "account_id required"})

    # ensure the account belongs to the user
    acc = get_object_or_404(BrokerAccount, id=account_id, user=user)

    # avoid duplicate link
    if AlgoBrokerLink.objects.filter(user=user, algo_id=algo_id, account_id=account_id).exists():
        return JsonResponse({"success": False, "error": "Account already linked"})

    link = AlgoBrokerLink.objects.create(
        user=user, algo_id=algo_id, account=acc, role=role, is_default=is_default
    )

    # keep one default per algo (across roles). If you prefer per-role defaults, filter by role here.
    if link.is_default:
        AlgoBrokerLink.objects.filter(user=user, algo_id=algo_id).exclude(id=link.id).update(is_default=False)

    return JsonResponse({"success": True})

# --- Accounts list used by the Register modal ---
def api_env_accounts(request):
    """
    GET -> {success:true, accounts:[{id,label,broker_name}]}
    """
    user = request.user
    accts = BrokerAccount.objects.filter(user=user).select_related("broker").order_by("label")
    out = [{"id": a.id, "label": a.label,"broker_id": a.broker_id, "broker_name": a.broker.broker_name} for a in accts]
    return JsonResponse({"success": True, "accounts": out})


def _algo_display_name(a):
    # Tries common fields safely
    for fld in ("name", "algo_name", "display_name", "title"):
        v = getattr(a, fld, None)
        if v: return v
    # Sometimes AlgorithmLogic has a FK named "algo" that has algo_name
    algo_obj = getattr(a, "algo", None)
    if algo_obj:
        for fld in ("algo_name", "name", "display_name"):
            v = getattr(algo_obj, fld, None)
            if v: return v
    return f"Algo #{getattr(a, 'id', '—')}"

def _safe_sum(qs, field):
    try:
        return qs.aggregate(x=Sum(field))["x"] or 0.0
    except Exception:
        return 0.0

def api_dashboard_algos(request):
    user = request.user

    try:
        algos = AlgorithmLogic.objects.all().order_by("id")
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Algo model query failed: {e}"}, status=500)

    # Try to load links/runs; if tables not migrated yet, fall back gracefully
    try:
        from core.models import AlgoBrokerLink, AlgoRun, DailyPnl
        links = AlgoBrokerLink.objects.filter(user=user, algo_id__in=algos.values_list("id", flat=True)).select_related("account","account__broker")
        links_by_algo = {}
        for l in links:
            links_by_algo.setdefault(l.algo_id, []).append(l)
    except Exception:
        links_by_algo = {}

    try:
        runs = AlgoRun.objects.filter(user=user, algo_id__in=algos.values_list("id", flat=True))
        runs_by_algo = {r.algo_id: r for r in runs if r.status != "stopped"}
    except Exception:
        runs_by_algo = {}

    payload = []
    today = date.today()
    start_month = today.replace(day=1)

    for a in algos:
        links = links_by_algo.get(a.id, [])
        run = runs_by_algo.get(a.id)

        # derive status
        if run:
            if run.status == "running":
                stale = getattr(run, "last_heartbeat", None)
                if stale and stale < timezone.now() - timedelta(seconds=30):
                    status = "error"
                else:
                    status = "running"
            else:
                status = run.status
        else:
            has_live = any(getattr(l, "role", "") != "paper" for l in links)
            has_paper = any(getattr(l, "role", "") == "paper" for l in links)
            status = "live_ready" if has_live else ("paper_ready" if has_paper else "unregistered")

        # KPIs (safe even if DailyPnl not ready)
        try:
            qs = DailyPnl.objects.filter(user=user, algo_id=a.id)
            today_pnl = _safe_sum(qs.filter(date=today), "pnl")
            mtd_pnl   = _safe_sum(qs.filter(date__gte=start_month), "pnl")
            total_pnl = _safe_sum(qs, "pnl")
        except Exception:
            today_pnl = mtd_pnl = total_pnl = 0.0

        payload.append({
            "algo_id": a.id,
            "algo_name": _algo_display_name(a),
            "status": status,
            "has_paper": any(getattr(l, "role", "") == "paper" for l in links),
            "has_live": any(getattr(l, "role", "") != "paper" for l in links),
            "run_mode": getattr(run, "mode", None),
            "last_heartbeat": getattr(run, "last_heartbeat", None).isoformat() if getattr(run, "last_heartbeat", None) else None,
            "kpis": {"today_pnl": round(today_pnl,2), "mtd_pnl": round(mtd_pnl,2), "total_pnl": round(total_pnl,2)},
        })

    return JsonResponse({"success": True, "algos": payload})

def api_status_styles(request):
    user = request.user if request.user.is_authenticated else None

    # Start with global rows
    styles = {s.key: s for s in AlgoStatusStyle.objects.filter(user__isnull=True, enabled=True)}
    # Overlay user-specific overrides
    if user:
        for s in AlgoStatusStyle.objects.filter(user=user, enabled=True):
            styles[s.key] = s

    payload = {}
    for key, s in styles.items():
        payload[key] = {
            "label": s.label or key.replace('_', ' ').title(),
            "bulma_tag_class": s.bulma_tag_class,
            "bulma_bg_class": s.bulma_bg_class,
            "dot_hex": s.dot_hex,
            "text_hex": s.text_hex,
        }
    return JsonResponse({"success": True, "styles": payload})


def dashboard_page(request):
    # Render with no heavy data; the page JS calls APIs.
    return render(request, "dashboard.html", {})


def _derive_status(links, run):
    """
    Card status logic:
      - running / paused / error if AlgoRun exists
      - else live_ready if any non-paper link
      - else paper_ready if any paper link
      - else unregistered
    """
    if run:
        if run.status == 'running':
            # Optional stale heartbeat check:
            if run.last_heartbeat and run.last_heartbeat < timezone.now() - timedelta(seconds=30):
                return 'error'
            return 'running'
        return run.status  # paused/stopped/error

    has_live = any(l.role != 'paper' for l in links)
    has_paper = any(l.role == 'paper' for l in links)
    if has_live: return 'live_ready'
    if has_paper: return 'paper_ready'
    return 'unregistered'

def _kpis_for(user, algo_id):
    """
    Compute quick KPIs from DailyPnl. You can expand this easily.
    """
    today = date.today()
    start_month = today.replace(day=1)

    qs = DailyPnl.objects.filter(user=user, algo_id=algo_id, mode__in=['paper','live'])
    today_pnl = qs.filter(date=today).aggregate(x=Sum('pnl'))['x'] or 0.0
    mtd_pnl   = qs.filter(date__gte=start_month).aggregate(x=Sum('pnl'))['x'] or 0.0
    total_pnl = qs.aggregate(x=Sum('pnl'))['x'] or 0.0

    return {
        "today_pnl": round(today_pnl, 2),
        "mtd_pnl": round(mtd_pnl, 2),
        "total_pnl": round(total_pnl, 2)
    }


@csrf_exempt
def api_dashboard_run(request, algo_id):
    """
    Body: { "mode": "paper"|"live", "account_id": optional }
    Picks an account (explicit or default) and sets AlgoRun.status='running'.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})
    user = request.user
    body = json.loads(request.body or "{}")
    mode = body.get("mode", "paper")
    account_id = body.get("account_id")

    # choose link
    link_q = AlgoBrokerLink.objects.filter(user=user, algo_id=algo_id)
    link = None
    if account_id:
        link = link_q.filter(account_id=account_id).first()
    else:
        if mode == 'paper':
            link = link_q.filter(role='paper', is_default=True).first() or link_q.filter(role='paper').first()
        else:
            live_q = link_q.exclude(role='paper')
            link = live_q.filter(is_default=True).first() or live_q.filter(role='primary').first() or live_q.first()

    if not link:
        return JsonResponse({"success": False, "error": "No linked account available for this mode."})

    run, _ = AlgoRun.objects.get_or_create(user=user, algo_id=algo_id, mode=mode)
    run.status = 'running'
    run.account_id = link.account_id
    run.last_heartbeat = timezone.now()
    run.last_error = ''
    run.save()

    # TODO: enqueue/notify your executor service to actually start
    return JsonResponse({"success": True})

@csrf_exempt
def api_dashboard_pause(request, algo_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})
    user = request.user
    body = json.loads(request.body or "{}")
    mode = body.get("mode", "paper")
    try:
        run = AlgoRun.objects.get(user=user, algo_id=algo_id, mode=mode)
        run.status = 'paused'
        run.save()
        return JsonResponse({"success": True})
    except AlgoRun.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not running"})

@csrf_exempt
def api_dashboard_stop(request, algo_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})
    user = request.user
    body = json.loads(request.body or "{}")
    mode = body.get("mode", "paper")
    AlgoRun.objects.filter(user=user, algo_id=algo_id, mode=mode).update(status='stopped')
    return JsonResponse({"success": True})

def api_dashboard_logs(request, algo_id):
    """
    GET /api/dashboard/<algo_id>/logs/?mode=paper|live&limit=50
    """
    user = request.user
    mode = request.GET.get("mode", "paper")
    limit = int(request.GET.get("limit", 50))
    rows = (ExecutionLog.objects
            .filter(user=user, algo_id=algo_id, mode=mode)
            .order_by('-ts')[:limit])
    out = [{"ts": r.ts.isoformat(), "level": r.level, "message": r.message} for r in rows]
    return JsonResponse({"success": True, "logs": out})

# views.py  (keep a single definition)
# core/views.py

@login_required
@require_POST
def api_test_function_code(request):
    """
    POST JSON:
      {
        "function_code": "<python>",
        "algo_id": 123,                # optional (used for merging globals and link picking)
        "mode": "paper"|"live",        # default "paper"
        "account_id": 45,              # optional (forces a specific account)
        "inputs": { ... },             # optional override for function inputs
        # convenience fallbacks if inputs not provided:
        "symbol": "NIFTY",
        "timeframe": "5m",
        "lookback": 120,
        "debug": true                  # optional: include debug info about env/client
      }
    """
    try:
        body = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid JSON body."}, status=400)

    code = (body.get("function_code") or "").strip()
    if not code:
        return JsonResponse({"success": False, "error": "function_code is required."}, status=400)

    algo_id    = body.get("algo_id")          # may be None
    mode       = (body.get("mode") or "paper").lower()
    account_id = body.get("account_id")
    debug      = bool(body.get("debug", False))

    # Build env (attaches paper client for paper mode, or a live client if live+account resolved)
    try:
        env = build_env(request.user, algo_id, mode=mode, account_id=account_id)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"env error: {e}"}, status=400)

    # Inputs: either explicit dict from the request, or simple defaults
    inputs = body.get("inputs")
    if not isinstance(inputs, dict):
        inputs = {
            "symbol":    body.get("symbol")    or "NIFTY",
            "timeframe": body.get("timeframe") or "5m",
            "lookback":  int(body.get("lookback") or 120),
        }

    # Execute user code
    try:
        result = execute_user_code(code, inputs, env)
        payload = {"success": True, "result": result}
        if debug:
            payload["debug"] = {
                "mode": mode,
                "has_client": bool(env.get("client")),
                "broker": env.get("broker"),
                "meta": env.get("meta"),
            }
        return JsonResponse(payload)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

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


def environment_page(request):
    brokers = Broker.objects.all().order_by('broker_name')
    algos = AlgorithmLogic.objects.all().order_by('id')
    return render(request, "variablerelated/environment.html", {"brokers": brokers, "algos": algos})

# ---------------- BrokerAccount ----------------
@csrf_exempt
def api_broker_accounts(request):
    user = request.user
    if request.method == "GET":
        accs = (BrokerAccount.objects
                .filter(user=user)
                .select_related('broker')
                .order_by('label'))
        data = [{
            "id": a.id,
            "label": a.label,
            "broker_id": a.broker_id,
            "broker_name": a.broker.broker_name,
            "broker_username": a.broker_username,
            "is_active": a.is_active,
            "last_test_at": a.last_test_at.isoformat() if a.last_test_at else None,
            "last_test_ok": a.last_test_ok,
            "last_error": a.last_error or ""
        } for a in accs]
        return JsonResponse({"success": True, "accounts": data})

    if request.method == "POST":
        try:
            body = json.loads(request.body)
            label = body["label"].strip()
            broker_id = body["broker_id"]
            broker_username = body["broker_username"].strip()

            # duplicate guards
            if BrokerAccount.objects.filter(user=user, label=label).exists():
                return JsonResponse({"success": False, "error": "Duplicate label."})
            if BrokerAccount.objects.filter(user=user, broker_id=broker_id, broker_username=broker_username).exists():
                return JsonResponse({"success": False, "error": "Duplicate broker username for this broker."})

            acc = BrokerAccount.objects.create(
                user=user,
                broker_id=broker_id,
                label=label,
                broker_username=broker_username,
                credentials=body.get("credentials") or {},
                is_active=bool(body.get("is_active", True)),
            )
            return JsonResponse({"success": True, "id": acc.id})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid method"})


@csrf_exempt
def api_broker_account_detail(request, acc_id):
    user = request.user
    acc = get_object_or_404(BrokerAccount, id=acc_id, user=user)
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            new_label = body.get("label", acc.label).strip()
            new_broker_id = body.get("broker_id", acc.broker_id)
            new_username = body.get("broker_username", acc.broker_username).strip()

            if new_label != acc.label and BrokerAccount.objects.filter(user=user, label=new_label).exists():
                return JsonResponse({"success": False, "error": "Duplicate label."})
            if (new_broker_id != acc.broker_id or new_username != acc.broker_username) and \
               BrokerAccount.objects.filter(user=user, broker_id=new_broker_id, broker_username=new_username).exclude(id=acc.id).exists():
                return JsonResponse({"success": False, "error": "Duplicate broker username for this broker."})

            acc.label = new_label
            acc.broker_id = new_broker_id
            acc.broker_username = new_username
            if "credentials" in body:
                acc.credentials = body["credentials"]
            if "is_active" in body:
                acc.is_active = bool(body["is_active"])
            acc.save()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    if request.method == "DELETE":
        acc.delete()
        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Invalid method"})


@csrf_exempt
def api_broker_account_test(request, acc_id):
    user = request.user
    acc = get_object_or_404(BrokerAccount, id=acc_id, user=user)
    try:
        root = acc.broker.root_api
        ok = True; err = ""
        try:
            req = urllib.request.Request(root, method="GET")
            with urllib.request.urlopen(req, timeout=5) as _:
                ok = True
        except Exception as ee:
            ok = False
            err = f"{type(ee).__name__}: {ee}"
        acc.last_test_at = timezone.now()
        acc.last_test_ok = ok
        acc.last_error = err[:2000]
        acc.save()
        return JsonResponse({"success": True, "ok": ok, "error": err})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

# ---------------- AlgoBrokerLink ----------------

@csrf_exempt
def api_links(request):
    user = request.user
    if request.method == "GET":
        algo_id = request.GET.get("algo")
        q = Q(user=user)
        if algo_id:
            q &= Q(algo_id=algo_id)
        links = (AlgoBrokerLink.objects
                 .filter(q)
                 .select_related('algo', 'account', 'account__broker')
                 .order_by('algo_id', '-is_default', 'role', 'account__label'))
        data = [{
            "id": l.id,
            "algo_id": l.algo_id,
            "algo_name": getattr(getattr(l.algo, 'algo', None), 'algo_name', f"Algo#{l.algo_id}"),
            "account_id": l.account_id,
            "account_label": l.account.label,
            "broker_name": l.account.broker.broker_name,
            "role": l.role,
            "is_default": l.is_default,
            "settings": l.settings or {},
        } for l in links]
        return JsonResponse({"success": True, "links": data})

    if request.method == "POST":
        try:
            body = json.loads(request.body)
            algo_id = body["algo_id"]
            account_id = body["account_id"]
            role = body.get("role", "primary")
            is_default = bool(body.get("is_default", False))
            settings = body.get("settings") or {}

            # dup: same (user, algo, account)
            if AlgoBrokerLink.objects.filter(user=user, algo_id=algo_id, account_id=account_id).exists():
                return JsonResponse({"success": False, "error": "This account is already linked to the algo."})

            link = AlgoBrokerLink.objects.create(
                user=user, algo_id=algo_id, account_id=account_id,
                role=role, is_default=is_default, settings=settings
            )
            # enforce one default per (user, algo)
            if is_default:
                AlgoBrokerLink.objects.filter(user=user, algo_id=algo_id).exclude(id=link.id).update(is_default=False)
            return JsonResponse({"success": True, "id": link.id})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid method"})


@csrf_exempt
def api_link_detail(request, link_id):
    user = request.user
    link = get_object_or_404(AlgoBrokerLink, id=link_id, user=user)
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            new_algo = body.get("algo_id", link.algo_id)
            new_account = body.get("account_id", link.account_id)
            new_role = body.get("role", link.role)
            new_is_default = bool(body.get("is_default", link.is_default))
            new_settings = body.get("settings", link.settings)

            if (new_algo != link.algo_id or new_account != link.account_id) and \
               AlgoBrokerLink.objects.filter(user=user, algo_id=new_algo, account_id=new_account).exclude(id=link.id).exists():
                return JsonResponse({"success": False, "error": "This account is already linked to the algo."})

            link.algo_id = new_algo
            link.account_id = new_account
            link.role = new_role
            link.is_default = new_is_default
            link.settings = new_settings
            link.save()

            if new_is_default:
                AlgoBrokerLink.objects.filter(user=user, algo_id=new_algo).exclude(id=link.id).update(is_default=False)

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    if request.method == "DELETE":
        link.delete()
        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Invalid method"})

# ---------------- Global Variables (same idea as before) ----------------

@csrf_exempt
def api_globals(request):
    user = request.user
    if request.method == "GET":
        scope = request.GET.get("scope")   # global|algo|user|all
        algo_id = request.GET.get("algo")
        q = Q()
        if scope == "global":
            q &= Q(algo__isnull=True, user__isnull=True)
        elif scope == "algo" and algo_id:
            q &= Q(algo_id=algo_id)
        elif scope == "user":
            q &= Q(user=user)
        gvs = GlobalVariable.objects.filter(q).order_by('key')
        data = [{
            "id": g.id, "key": g.key, "value": g.value, "dtype": g.dtype,
            "algo": g.algo_id, "user": g.user_id
        } for g in gvs]
        return JsonResponse({"success": True, "globals": data})

    if request.method == "POST":
        body = json.loads(request.body)
        key = body["key"].strip()
        scope = body.get("scope", "global")
        algo_id = body.get("algo") if scope == "algo" else None
        user_scope = user if scope == "user" else None
        if GlobalVariable.objects.filter(key=key, algo_id=algo_id, user=user_scope).exists():
            return JsonResponse({"success": False, "error": "Duplicate key in this scope."})
        gv = GlobalVariable.objects.create(
            key=key, dtype=body.get("dtype","text"), value=body.get("value"),
            algo_id=algo_id, user=user_scope
        )
        return JsonResponse({"success": True, "id": gv.id})

    return JsonResponse({"success": False, "error": "Invalid method"})


@csrf_exempt
def api_global_detail(request, gv_id):
    user = request.user
    gv = get_object_or_404(GlobalVariable, id=gv_id)
    if request.method == "POST":
        body = json.loads(request.body)
        new_key = body.get("key", gv.key).strip()
        scope = body.get("scope", "global")
        new_algo = body.get("algo") if scope == "algo" else None
        new_user = user if scope == "user" else None
        if GlobalVariable.objects.filter(key=new_key, algo_id=new_algo, user=new_user).exclude(id=gv.id).exists():
            return JsonResponse({"success": False, "error": "Duplicate key in this scope."})
        gv.key = new_key
        gv.dtype = body.get("dtype", gv.dtype)
        gv.value = body.get("value")
        gv.algo_id = new_algo
        gv.user = new_user
        gv.save()
        return JsonResponse({"success": True})

    if request.method == "DELETE":
        gv.delete()
        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Invalid method"})


# MAIN PAGE
def variable_parameters_page(request):
    categories = VariableCategory.objects.all().order_by('name')
    current_category = categories.first() if categories else None
    variables = Variable.objects.filter(category=current_category) if current_category else []
    all_parameters = VariableParameter.objects.all()
    return render(request, "variablerelated/Variable_Parameters.html", {
        "categories": categories,
        "current_category": current_category,
        "variables": variables,
        "all_parameters": all_parameters,
    })

# ---- AJAX API ENDPOINTS ----

@csrf_exempt
def api_variables(request):
    if request.method == "GET":
        category_id = request.GET.get("category")
        variables = Variable.objects.filter(category_id=category_id) if category_id else Variable.objects.all()
        data = []
        for var in variables:
            data.append({
                "id": var.id,
                "name": var.name,
                "display_name": var.display_name,
                "category": var.category.id,
                "parameters": [p.id for p in var.parameters.all()],
                "description": getattr(var, "description", ""),
                "function_code": var.function_code or "",
            })
        return JsonResponse({"success": True, "variables": data})
    elif request.method == "POST":
        data = json.loads(request.body)
        # Handle create variable
        var = Variable.objects.create(
            name=data["name"],
            display_name=data["display_name"],
            category_id=data["category"],
            function_code=data.get("function_code") or "",
        )
        var.parameters.set(data.get("parameters", []))
        var.save()
        return JsonResponse({"success": True, "id": var.id})
    return JsonResponse({"success": False, "error": "Invalid method"})

@csrf_exempt
def api_variable_detail(request, var_id):
    var = get_object_or_404(Variable, id=var_id)
    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "variable": {
                "id": var.id,
                "name": var.name,
                "display_name": var.display_name,
                "category": var.category.id,
                "parameters": [p.id for p in var.parameters.all()],
                "description": getattr(var, "description", ""),
                "function_code": var.function_code or "",
            }
        })
    elif request.method == "POST":
        data = json.loads(request.body)
        var.name = data["name"]
        var.display_name = data["display_name"]
        var.category_id = data["category"]
        var.function_code = data.get("function_code") or ""
        var.parameters.set(data.get("parameters", []))
        var.save()
        return JsonResponse({"success": True})
    elif request.method == "DELETE":
        var.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Invalid method"})

@csrf_exempt
def api_categories(request):
    if request.method == "GET":
        cats = VariableCategory.objects.all().order_by("name")
        data = [{"id": c.id, "name": c.name} for c in cats]
        return JsonResponse({"success": True, "categories": data})
    elif request.method == "POST":
        data = json.loads(request.body)
        cat = VariableCategory.objects.create(name=data["name"])
        return JsonResponse({"success": True, "id": cat.id})
    return JsonResponse({"success": False})

@csrf_exempt
def api_parameters(request):
    if request.method == "GET":
        params = VariableParameter.objects.all().order_by("name")
        data = []
        for p in params:
            data.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "input_type": p.input_type,
                "default_value": p.default_value,
                "allowed_values": getattr(p, "allowed_values", ""),
            })
        return JsonResponse({"success": True, "parameters": data})
    elif request.method == "POST":
        data = json.loads(request.body)
        param = VariableParameter.objects.create(
            name=data["name"],
            description=data.get("description", ""),
            input_type=data["input_type"],
            default_value=data.get("default_value", ""),
            # Save allowed_values if your model supports it
        )
        return JsonResponse({"success": True, "id": param.id})
    return JsonResponse({"success": False})

@csrf_exempt
def api_parameter_detail(request, param_id):
    param = get_object_or_404(VariableParameter, id=param_id)
    if request.method == "POST":
        data = json.loads(request.body)
        param.name = data["name"]
        param.description = data.get("description", "")
        param.input_type = data["input_type"]
        param.default_value = data.get("default_value", "")
        if hasattr(param, "allowed_values"):
            param.allowed_values = data.get("allowed_values", "")
        param.save()
        return JsonResponse({"success": True})
    elif request.method == "DELETE":
        param.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False})


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
    name = (request.GET.get('name') or '').strip()
    exclude_id = request.GET.get('exclude_id')
    qs = AlgoList.objects.filter(algo_name__iexact=name)
    if exclude_id:
      qs = qs.exclude(pk=exclude_id)
    if not name:
      return JsonResponse({'valid': False, 'message': 'Algorithm name is required.'})
    if qs.exists():
      return JsonResponse({'valid': False, 'message': 'This algorithm name is already taken.'})
    return JsonResponse({'valid': True})

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
    user_algos = AlgoBrokerLink.objects.filter(user=request.user)
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
            authenticator_req=data.get('AuthenticatorReq'),
            adapter_path=data.get('AdapterPath')
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
        name = request.POST.get("AlgoName")
        fund = request.POST.get("Minimum_Fund_Reqd")
        desc = request.POST.get("Algo_description")
        
        algo.algo_name         = name
        algo.minimum_fund_reqd = fund
        algo.algo_description  = desc
        algo.updated_at        = timezone.now()
        algo.save()
        # Save user-defined variables
        UserDefinedVariable.objects.filter(algo=algo, user=request.user).delete()
        for key, raw_json in request.POST.items():
            if not key.startswith("user_variable_json_"):
                continue
            try:
                data = json.loads(raw_json)
                var_name = data.get("name")
                var_expr = data.get("expression")
                if var_name and isinstance(var_expr, list):
                    UserDefinedVariable.objects.create(
                        algo=algo,
                        user=request.user,
                        name=var_name,
                        expression=var_expr
                    )
            except json.JSONDecodeError:
                # you might want to log or message this
                continue
        AlgorithmLogic.objects.filter(algo=algo).delete()
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

        messages.success(request, "✅ Algorithm updated successfully")
        return redirect("algo_list")
    

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
    symbol_list_json = json.dumps(sorted(set(all_symbols)),cls=DjangoJSONEncoder)

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
    user_variables = UserDefinedVariable.objects.filter(algo=algo, user=request.user)
    user_vars_json = json.dumps([
        {"name": v.name, "expression": v.expression} for v in user_variables
    ], cls=DjangoJSONEncoder)

    # Serialize existing conditions
    logic_entries=AlgorithmLogic.objects.filter(algo=algo)
    legs_data = []
    for leg in logic_entries:
        legs_data.append({
            "num_stocks": leg.num_stocks,
            "instrument_name": leg.instrument_name,
            "expiry_date": leg.expiry_date,
            "strike_price": leg.strike_price,
            "option_type": leg.option_type,
            "order_type": leg.order_type,
            "order_direction": leg.order_direction,
            "entry_conditions": serialize_conditions(leg, "entry"),
            "exit_conditions": serialize_conditions(leg, "exit"),
        })

    return render(request, "algorelated/edit_algo.html", {
        "algo": algo,
        "is_edit_mode": True,
        "instruments_json":mark_safe(instruments_json),
        "symbol_list_json": mark_safe(symbol_list_json),
        "indicators_json": mark_safe(indicators_json),
        "user_vars_json": mark_safe(user_vars_json),
        "legs_json": mark_safe(json.dumps(legs_data,cls=DjangoJSONEncoder)),
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

def get_minimum_fund(request):
    algo_id = request.GET.get('algo_id')
    try:
        algo = AlgoList.objects.get(id=algo_id)
        return JsonResponse({'minimum_fund': algo.minimum_fund_reqd})
    except AlgoList.DoesNotExist:
        return JsonResponse({'error': 'Algo not found'}, status=404)

# ---------- Extra ----------
def index(request):
    return render(request, 'core/index.html')


