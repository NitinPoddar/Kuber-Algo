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
from .forms import SimpleSignupForm, AlgorithmForm,ProfileForm,PasswordChangeForm
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
# Auth + user helpers
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, get_user_model
from django.http import HttpResponseBadRequest
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
User = get_user_model()

# If not already imported:
from django.db import models  # for Q in login lookup (optional if you already use Q)
User = get_user_model()

# OTP model

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
    AlgoRun,
    DailyPnl,
    ExecutionLog,
    AlgoStatusStyle,
    AlgoOffer, 
    AlgoPlan,
    AlgoInvitation, 
    AlgoSubscription, 
    AlgoEntitlement,
    OTP,
    PendingSignup,
    PendingContactChange,
    Exchange,
    AlgoRule
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
# views.py (add near top)
from django.utils.text import slugify
from django.contrib.auth import get_user_model

User = get_user_model()

def _make_unique_username(seed: str) -> str:
    base = slugify(seed.split("@")[0]) or "user"
    candidate, i = base, 0
    while User.objects.filter(username=candidate).exists():
        i += 1
        candidate = f"{base}{i}"
    return candidate

def signup_view(request):
    if request.method == "POST":
        form = SimpleSignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            phone = form.cleaned_data["phone"].strip()
            pwd1  = form.cleaned_data["password1"]
            pwd2  = form.cleaned_data["password2"]

            # server-side guards
            if pwd1 != pwd2:
                messages.error(request, "Passwords do not match.")
                return render(request, "registration/signup.html", {"form": form, "stage": "form"})

            if User.objects.filter(email__iexact=email).exists():
                messages.error(request, "This email is already registered.")
                return render(request, "registration/signup.html", {"form": form, "stage": "form"})

            if User.objects.filter(phone=phone).exists():
                messages.error(request, "This mobile number is already registered.")
                return render(request, "registration/signup.html", {"form": form, "stage": "form"})

            # Create a pending signup (no user row yet)
            ps = PendingSignup.start(email=email, phone=phone, raw_password=pwd1, ttl_seconds=600)
            request.session["pending_signup_token"] = ps.token

            # DEV: print distinct codes to console
            print(f"[SIGNUP][EMAIL] code for {ps.email}: {ps.email_code}")
            print(f"[SIGNUP][PHONE] code for {ps.phone}: {ps.phone_code}")

            return render(request, "registration/signup.html", {
                "stage": "otp",
                "email": _mask_email(email),
                "phone": _mask_phone(phone),
                "otp_cooldown": 30
            })
    else:
        form = SimpleSignupForm()

    return render(request, "registration/signup.html", {"form": form, "stage": "form"})

def verify_signup_codes(request):
    """POST from the OTP step — creates the real user only after both codes verify."""
    if request.method != "POST":
        return redirect("signup")

    token = request.session.get("pending_signup_token")
    if not token:
        messages.error(request, "Your verification session expired. Please sign up again.")
        return redirect("signup")

    ps = get_object_or_404(PendingSignup, token=token)
    if ps.expired():
        ps.delete()
        messages.error(request, "Codes expired. Please sign up again.")
        return redirect("signup")

    email_code = (request.POST.get("email_code") or "").strip()
    phone_code = (request.POST.get("phone_code") or "").strip()

    err = False
    if email_code != ps.email_code:
        messages.error(request, "The email code is invalid.")
        err = True
    if phone_code != ps.phone_code:
        messages.error(request, "The phone code is invalid.")
        err = True
    if err:
        return render(request, "registration/signup.html", {
            "stage": "otp",
            "email": _mask_email(ps.email),
            "phone": _mask_phone(ps.phone),
            "otp_cooldown": 15
        })

    # Create the actual user now
    # You can set username = email or generate one; using email keeps it simple
    user = User.objects.create(
        username=ps.email,
        email=ps.email,
        phone=ps.phone,
        is_email_verified=True,
        is_phone_verified=True,
        password=ps.password_hash,  # already hashed
    )

    # Cleanup
    ps.delete()
    request.session.pop("pending_signup_token", None)

    # Log them in and go to dashboard
    auth_login(request, user)
    return redirect("dashboard_page")

def resend_signup_codes(request):
    """POST — regenerates both codes on the pending signup and re-renders OTP step."""
    if request.method != "POST":
        return redirect("signup")

    token = request.session.get("pending_signup_token")
    if not token:
        messages.error(request, "Your verification session expired.")
        return redirect("signup")

    ps = get_object_or_404(PendingSignup, token=token)
    if ps.expired():
        ps.delete()
        messages.error(request, "Codes expired. Please sign up again.")
        return redirect("signup")

    ps.email_code = PendingSignup.gen_code()
    ps.phone_code = PendingSignup.gen_code()
    ps.expires_at = timezone.now() + timezone.timedelta(minutes=10)
    ps.save(update_fields=["email_code", "phone_code", "expires_at"])

    print(f"[SIGNUP][EMAIL][RESEND] {ps.email}: {ps.email_code}")
    print(f"[SIGNUP][PHONE][RESEND] {ps.phone}: {ps.phone_code}")
    messages.success(request, "New codes sent.")

    return render(request, "registration/signup.html", {
        "stage": "otp",
        "email": _mask_email(ps.email),
        "phone": _mask_phone(ps.phone),
        "otp_cooldown": 30
    })

# views.py

def _mask_email(e):
    if not e: return ""
    try:
        name, dom = e.split("@", 1)
        if len(name) <= 2: name_mask = name[:1] + "•"*(len(name)-1)
        else: name_mask = name[0] + "•"*(len(name)-2) + name[-1]
        return f"{name_mask}@{dom}"
    except Exception:
        return e

def _mask_phone(p):
    if not p: return ""
    p = str(p)
    if len(p) <= 4: return "•"*len(p)
    return "•"*(len(p)-4) + p[-4:]

@require_http_methods(["GET", "POST"])
def verify_otp_view(request):
    """Inline verification flow: reuses registration/signup.html with stage='otp'."""
    uid = request.session.get("pending_user_id")
    if not uid:
        messages.error(request, "Your verification session expired. Please sign up or log in again.")
        return redirect("signup")
    user = get_object_or_404(User, id=uid)

    if request.method == "GET":
        ctx = {
            "stage": "otp",
            "email": _mask_email(getattr(user, "email", "")),
            "phone": _mask_phone(getattr(user, "phone", "")),
            "otp_cooldown": 30,  # seconds
        }
        return render(request, "registration/signup.html", ctx)

    # POST: verify codes
    email_code = (request.POST.get("email_code") or "").strip()
    phone_code = (request.POST.get("phone_code") or "").strip()
    single_code = (request.POST.get("otp_code") or "").strip()

    if single_code and not email_code and not phone_code:
        # allow single-code flow to satisfy both
        email_code = phone_code = single_code

    err = False
    now = timezone.now()
    valid_purposes = ["verify", "signup", "login"]  # accept any for dev simplicity

    # verify email
    if user.email:
        otp_email = (OTP.objects
                     .filter(user=user, purpose__in=valid_purposes, channel="email",
                             code=email_code, is_used=False, expires_at__gte=now)
                     .order_by("-created_at").first())
        if not otp_email or not otp_email.is_valid(email_code):
            messages.error(request, "The email code is invalid or expired.")
            err = True

    # verify phone
    if user.phone:
        otp_phone = (OTP.objects
                     .filter(user=user, purpose__in=valid_purposes, channel="phone",
                             code=phone_code, is_used=False, expires_at__gte=now)
                     .order_by("-created_at").first())
        if not otp_phone or not otp_phone.is_valid(phone_code):
            messages.error(request, "The phone code is invalid or expired.")
            err = True

    if err:
        ctx = {
            "stage": "otp",
            "email": _mask_email(getattr(user, "email", "")),
            "phone": _mask_phone(getattr(user, "phone", "")),
            "otp_cooldown": 15,  # shorter resend on retry
        }
        return render(request, "registration/signup.html", ctx)

    # mark used
    if user.email:
        OTP.objects.filter(user=user, purpose__in=valid_purposes,
                           channel="email", code=email_code, is_used=False).update(is_used=True)
    if user.phone:
        OTP.objects.filter(user=user, purpose__in=valid_purposes,
                           channel="phone", code=phone_code, is_used=False).update(is_used=True)

    # flip flags
    if hasattr(user, "is_email_verified") and user.email:
        user.is_email_verified = True
    if hasattr(user, "is_phone_verified") and user.phone:
        user.is_phone_verified = True
    user.save(update_fields=["is_email_verified", "is_phone_verified"] if hasattr(user, "is_email_verified") else ["date_joined"])

    # log them in and clear session
    auth_login(request, user)
    request.session.pop("pending_user_id", None)
    return redirect("dashboard_page")

def check_unique(request):
    email = (request.GET.get('email') or '').strip().lower()
    phone = (request.GET.get('phone') or '').strip()

    # exclude the current user automatically when logged in
    exclude_id = request.user.id if request.user.is_authenticated else None

    out = {}
    if email:
        qs = User.objects.filter(email__iexact=email)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        out['email_exists'] = qs.exists()
    if phone:
        qs = User.objects.filter(phone=phone)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        out['phone_exists'] = qs.exists()
    return JsonResponse(out)


@require_POST
def resend_otps(request):
    uid = request.session.get("pending_user_id")
    if not uid:
        messages.error(request, "Your verification session expired. Please sign up again.")
        return redirect("signup")

    user = get_object_or_404(User, id=uid)
    OTP.create_dual_distinct(user, purpose="verify", ttl_seconds=600)
    messages.success(request, "We’ve sent new codes to your email and mobile.")

    # Re-render inline OTP stage on the same signup page
    ctx = {
        "stage": "otp",
        "email": _mask_email(getattr(user, "email", "")),
        "phone": _mask_phone(getattr(user, "phone", "")),
        "otp_cooldown": 30,
    }
    return render(request, "registration/signup.html", ctx)
import re
User = get_user_model()

# simple detectors
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?\d{7,15}$")


def _find_user_by_identifier(identifier: str):
    identifier = (identifier or "").strip()
    if _EMAIL_RE.match(identifier):
        return User.objects.filter(email__iexact=identifier).first(), "email"
    if _PHONE_RE.match(identifier):
        return User.objects.filter(phone=identifier).first(), "phone"
    # treat as not found (we only accept email/phone)
    return None, None

# make sure these exist in your project:
# - OTP model with: code, purpose, channel, is_used, created_at, expires_at
#   methods: generate_code(), is_valid(self, code), and optionally create_dual_login_otp(user, ttl_seconds)
# - helper: _find_user_by_identifier(identifier) -> (user, "email"|"phone"|None)



@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    3-step UX in one template:
      stage = 'identify' -> collect email/phone only
      stage = 'password' -> ask password, offer "login with otp"
      stage = 'otp'      -> enter otp sent to email+phone (same code)
    """
    stage = "identify"
    ctx = {"stage": stage, "identifier": ""}

    if request.method == "GET":
        return render(request, "registration/login.html", {"stage": "identify", "identifier": ""})

    # POST
    action = (request.POST.get("action") or "start").strip()
    identifier = (request.POST.get("identifier") or "").strip()
    ctx["identifier"] = identifier

    # ---- STEP 1: start (identify) ----
    if action == "start":
        user, _ = _find_user_by_identifier(identifier)
        if not user:
            messages.error(request, "Please enter a valid registered email address or mobile number.")
            return render(request, "registration/login.html", ctx)

        if not (user.is_active and getattr(user, "is_email_verified", False) and getattr(user, "is_phone_verified", False)):
            # hand off to your existing verification flow
            request.session["pending_user_id"] = user.id  # helpful for /verify-otp/
            messages.error(request, "Your account isn’t verified yet. Please complete verification.")
            return redirect("verify_otp")

        request.session["login_uid"] = user.id
        request.session["login_identifier"] = identifier
        ctx.update({"stage": "password"})
        return render(request, "registration/login.html", ctx)

    # Need a user in session for the next actions
    uid = request.session.get("login_uid")
    if not uid:
        messages.error(request, "Your login session expired. Please enter your email or phone again.")
        return render(request, "registration/login.html", {"stage": "identify", "identifier": ""})
    user = get_object_or_404(User, id=uid)

    # Re-guard verified/active
    if not (user.is_active and getattr(user, "is_email_verified", False) and getattr(user, "is_phone_verified", False)):
        request.session["pending_user_id"] = user.id
        messages.error(request, "Your account isn’t verified yet. Please complete verification.")
        return redirect("verify_otp")

    # ---- STEP 2a: password login ----
    if action == "password":
        password = request.POST.get("password") or ""
        authed = authenticate(request, username=user.username, password=password)
        if not authed:
            messages.error(request, "Incorrect password. Please try again.")
            return render(request, "registration/login.html", {"stage": "password", "identifier": request.session.get("login_identifier", "")})

        auth_login(request, authed)
        return redirect("dashboard_page")  # ensure this URL name exists

    # ---- STEP 2b: send OTP (same code to email+phone) ----
    if action == "send_otp":
        # Use ONE helper that creates both rows & prints to console (dev)
        # If you didn’t add create_dual_login_otp, see note below for inline version.
        OTP.create_dual_login_otp(user, ttl_seconds=600)
        messages.success(request, "We sent an OTP to your email and phone.")
        return render(request, "registration/login.html", {"stage": "otp", "identifier": request.session.get("login_identifier", "")})

    # ---- STEP 3: verify OTP ----
    if action == "verify_otp":
        otp_code = (request.POST.get("otp_code") or "").strip()
        if not otp_code:
            messages.error(request, "Enter the 6-digit OTP.")
            return render(request, "registration/login.html", {"stage": "otp", "identifier": request.session.get("login_identifier", "")})

        # accept if there's any unexpired, unused login OTP with this code (email or phone)
        otp = (OTP.objects
               .filter(user=user, purpose="login", is_used=False, code=otp_code)
               .order_by("-created_at")
               .first())
        if not otp or not otp.is_valid(otp_code):
            messages.error(request, "Invalid or expired OTP. Please try again.")
            return render(request, "registration/login.html", {"stage": "otp", "identifier": request.session.get("login_identifier", "")})

        # mark all matching login OTPs with this code as used
        OTP.objects.filter(user=user, purpose="login", code=otp_code, is_used=False).update(is_used=True)

        auth_login(request, user)
        return redirect("dashboard_page")

    # Fallback: go back to identify
    return render(request, "registration/login.html", {"stage": "identify", "identifier": ""})

# keep this version if you already have it
def logout_view(request):
    if request.method == "POST":
        auth_logout(request)
        messages.success(request, "Logged out.")
        return redirect("login")
    # GET just shows a confirm page with a POST button
    return render(request, "registration/logout.html")

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
@require_http_methods(["GET"])
def profile_page(request):
    """
    Show user profile, verification badges, edit form, OTP resend, and password change form.
    """
    form = ProfileForm(instance=request.user, user=request.user)
    pwd_form = PasswordChangeForm(user=request.user)
    return render(request, "accounts/profile.html", {
        "form": form,
        "pwd_form": pwd_form,
        "email_verified": getattr(request.user, "is_email_verified", False),
        "phone_verified": getattr(request.user, "is_phone_verified", False),
    })

@login_required
def profile_view(request):
    return render(request, "core/profile.html", {
        "user": request.user,
    })

@login_required
@require_http_methods(["POST"])
def start_contact_change(request):
    field = (request.POST.get("field") or "").strip()  # "email"|"phone"
    new_value = (request.POST.get("new_value") or "").strip()

    if field not in ("email","phone"):
        return JsonResponse({"ok":False,"error":"Invalid field"}, status=400)

    # uniqueness server-side
    if field == "email":
        if User.objects.filter(email__iexact=new_value).exists():
            return JsonResponse({"ok":False, "error":"This email is already taken."}, status=400)
    else:
        if User.objects.filter(phone=new_value).exists():
            return JsonResponse({"ok":False, "error":"This phone is already taken."}, status=400)

    code = PendingContactChange.gen_code()
    pcc = PendingContactChange.objects.create(
        user=request.user, field=field, new_value=new_value,
        code=code, expires_at=timezone.now()+timezone.timedelta(minutes=10)
    )

    # DEV: print
    if field == "email":
        print(f"[CONTACT CHANGE][EMAIL] {request.user.username} -> {new_value} code: {code}")
    else:
        print(f"[CONTACT CHANGE][PHONE] {request.user.username} -> {new_value} code: {code}")

    return JsonResponse({"ok":True})

@login_required
@require_http_methods(["POST"])
def verify_contact_change(request):
    field = (request.POST.get("field") or "").strip()
    code  = (request.POST.get("code") or "").strip()
    pcc = (PendingContactChange.objects
           .filter(user=request.user, field=field, code=code, expires_at__gte=timezone.now())
           .order_by("-created_at").first())
    if not pcc:
        return JsonResponse({"ok":False,"error":"Invalid or expired code."}, status=400)

    # apply change
    if field == "email":
        request.user.email = pcc.new_value
        if hasattr(request.user, "is_email_verified"):
            request.user.is_email_verified = True
    else:
        request.user.phone = pcc.new_value
        if hasattr(request.user, "is_phone_verified"):
            request.user.is_phone_verified = True
    request.user.save()
    pcc.delete()
    return JsonResponse({"ok":True})

from django.contrib.auth import update_session_auth_hash

@login_required
@require_http_methods(["POST"])
def change_password_with_current(request):
    cur = request.POST.get("current_password") or ""
    new1 = request.POST.get("new_password1") or ""
    new2 = request.POST.get("new_password2") or ""
    if new1 != new2:
        return JsonResponse({"ok":False,"error":"Passwords do not match."}, status=400)
    if not request.user.check_password(cur):
        return JsonResponse({"ok":False,"error":"Current password is incorrect."}, status=400)
    request.user.set_password(new1)
    request.user.save()
    update_session_auth_hash(request, request.user)  # keep user logged in
    return JsonResponse({"ok":True})

# send OTPs (distinct, to verified email/phone)
# views.py

import random

def _six():
    return f"{random.randint(0, 999999):06d}"

@login_required
@require_POST
def start_password_change_otp(request):
    """
    Generate ONE code; store it against both channels (email & phone) so either can validate it.
    Prints to console for dev.
    """
    code = _six()
    expires = timezone.now() + timezone.timedelta(minutes=10)

    # Clean any old password-otp rows for this user to avoid confusion
    PendingContactChange.objects.filter(
        user=request.user, field__in=["email", "phone"], new_value__in=[request.user.email, request.user.phone]
    ).delete()

    # Create two rows with SAME code (if channels exist)
    if request.user.email:
        PendingContactChange.objects.create(
            user=request.user, field="email", new_value=request.user.email,
            code=code, expires_at=expires
        )
        print(f"[PWD-OTP][EMAIL] {request.user.email}: {code}")

    if request.user.phone:
        PendingContactChange.objects.create(
            user=request.user, field="phone", new_value=request.user.phone,
            code=code, expires_at=expires
        )
        print(f"[PWD-OTP][PHONE] {request.user.phone}: {code}")

    return JsonResponse({"ok": True, "expires_in": 600})


@login_required
@require_POST
def verify_password_change_otp(request):
    """
    Accept ONE code; if it matches on either email or phone (not expired), allow password change.
    """
    code = (request.POST.get("otp_code") or "").strip()
    new1 = request.POST.get("new_password1") or ""
    new2 = request.POST.get("new_password2") or ""

    if not code:
        return JsonResponse({"ok": False, "error": "Enter the OTP code."}, status=400)
    if new1 != new2:
        return JsonResponse({"ok": False, "error": "Passwords do not match."}, status=400)

    now = timezone.now()
    has_match = PendingContactChange.objects.filter(
        user=request.user,
        field__in=["email", "phone"],
        new_value__in=[request.user.email, request.user.phone],
        code=code,
        expires_at__gte=now
    ).exists()

    if not has_match:
        return JsonResponse({"ok": False, "error": "Invalid or expired OTP."}, status=400)

    # Clear any active password-change OTPs for safety
    PendingContactChange.objects.filter(
        user=request.user, field__in=["email","phone"], new_value__in=[request.user.email, request.user.phone]
    ).delete()

    # Set password
    request.user.set_password(new1)
    request.user.save()
    update_session_auth_hash(request, request.user)  # keep user logged in
    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["POST"])
def profile_update(request):
    """
    Save edits. If email/phone changed, mark as unverified and trigger OTP flow.
    """
    user = request.user
    old_email = (user.email or "").lower()
    old_phone = user.phone or ""

    form = ProfileForm(request.POST, instance=user, user=user)
    if not form.is_valid():
        # re-render with errors
        pwd_form = PasswordChangeForm(user=user)
        return render(request, "accounts/profile.html", {
            "form": form,
            "pwd_form": pwd_form,
            "email_verified": getattr(user, "is_email_verified", False),
            "phone_verified": getattr(user, "is_phone_verified", False),
        })

    # Save core fields
    user = form.save(commit=False)

    email_changed = (old_email != (user.email or "").lower())
    phone_changed = (old_phone != (user.phone or ""))

    # If either changed, mark unverified and send OTPs
    send_any_otp = False
    if email_changed:
        user.is_email_verified = False
        send_any_otp = True
    if phone_changed:
        user.is_phone_verified = False
        send_any_otp = True

    user.save()

    if send_any_otp:
        # create OTPs for changed channels only
        if email_changed:
            OTP.create_otp(user, purpose="signup", channel="email", ttl_seconds=600)
            # TODO: send email OTP via your email gateway
        if phone_changed:
            OTP.create_otp(user, purpose="signup", channel="phone", ttl_seconds=600)
            # TODO: send SMS OTP via your SMS gateway

        # direct user to verify page (reuse your existing verify_otp flow)
        request.session["pending_user_id"] = user.id
        messages.info(request, "We sent new verification codes. Please verify your email and phone.")
        return redirect("verify_otp")

    messages.success(request, "Profile updated.")
    return redirect("profile_page")


@login_required
@require_POST
def profile_resend_otps(request):
    """
    Resend verification codes for both channels if not verified.
    """
    user = request.user
    any_sent = False
    if not getattr(user, "is_email_verified", False) and user.email:
        OTP.create_otp(user, purpose="signup", channel="email", ttl_seconds=600)
        any_sent = True
        # TODO: send email
    if not getattr(user, "is_phone_verified", False) and user.phone:
        OTP.create_otp(user, purpose="signup", channel="phone", ttl_seconds=600)
        any_sent = True
        # TODO: send SMS

    if any_sent:
        request.session["pending_user_id"] = user.id
        messages.success(request, "Verification codes sent. Please check your email/SMS.")
        return redirect("verify_otp")

    messages.info(request, "Your email and phone are already verified.")
    return redirect("profile_page")


@login_required
@require_http_methods(["POST"])
def profile_change_password(request):
    """
    Change password using Django's PasswordChangeForm.
    """
    form = PasswordChangeForm(user=request.user, data=request.POST)
    if form.is_valid():
        user = form.save()
        # Keep the user logged in
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been updated.")
        return redirect("profile_page")

    # re-render with errors
    prof_form = ProfileForm(instance=request.user, user=request.user)
    return render(request, "accounts/profile.html", {
        "form": prof_form,
        "pwd_form": form,
        "email_verified": getattr(request.user, "is_email_verified", False),
        "phone_verified": getattr(request.user, "is_phone_verified", False),
    })



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

def build_instruments_context():
    """
    Returns:
      segments_json: JSON string for active exchange keys (e.g., ["NFO","NSE","BSE","MCX"])
      instruments_by_segment_json: JSON string mapping segment -> list of instruments meta
      symbol_list_json: JSON string of unique instrument names (optional, e.g. for select2 search)
    """
    # Segments from DB (active only)
    seg_qs = Exchange.objects.filter(is_active=True).order_by("key").values_list("key", flat=True)
    segments = list(seg_qs)

    instruments = InstrumentList.objects.all()
    instruments_by_segment = {}   # { seg: { name: {expiries:set, strikes:set, lotsize:int} } }
    all_names = set()

    for inst in instruments:
        seg = getattr(inst, "exch_seg", None) or "NFO"
        if segments and seg not in segments:
            # if you want to include only active segments; otherwise remove this guard
            continue
        by_name = instruments_by_segment.setdefault(seg, {})
        meta = by_name.setdefault(inst.name, {"expiries": set(), "strikes": set(), "lotsize": inst.lotsize})
        all_names.add(inst.name)
        if inst.expiry:
            meta["expiries"].add(inst.expiry)
        if inst.strike is not None:
            meta["strikes"].add(inst.strike)
        if not meta.get("lotsize") and inst.lotsize:
            meta["lotsize"] = inst.lotsize

    instruments_json = {
        seg: [
            {
                "name": name,
                "expiries": sorted(meta["expiries"]),
                "strikes": sorted(meta["strikes"]),
                "lotsize": meta["lotsize"] or 0
            }
            for name, meta in by_name.items()
        ]
        for seg, by_name in instruments_by_segment.items()
    }

    segments_json = json.dumps(segments, cls=DjangoJSONEncoder)
    instruments_by_segment_json = json.dumps(instruments_json, cls=DjangoJSONEncoder)
    symbol_list_json = json.dumps(sorted(all_names), cls=DjangoJSONEncoder)

    return segments_json, instruments_by_segment_json, symbol_list_json

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

from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.http import HttpRequest, HttpResponse
import uuid

def _normalize_json_field(value, default=None):
    """
    Ensure a field is stored as a dict (not string).
    """
    if default is None:
        default = {}
    if value is None:
        return default
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default
def _save_rules_for_algo(algo, legs, rules_json):
    """Save rules array from frontend into AlgoRule rows."""
    AlgoRule.objects.filter(algo=algo).delete()
    try:
        rules = json.loads(rules_json or "[]")
    except Exception:
        rules = []

    for r in rules:
        leg = None
        if r.get("scope") == "LEG":
            # Match leg by index if provided
            idx = r.get("leg_index")
            if idx is not None and idx < len(legs):
                leg = legs[idx]

        AlgoRule.objects.create(
            algo=algo,
            leg=leg,
            rule_id=r.get("rule_id") or str(uuid.uuid4()),
            rule_type=r.get("rule_type", "ENTRY"),
            scope=r.get("scope", "LEG"),
            trigger_event=r.get("trigger_event", "ON_CONDITION"),
            priority=r.get("priority", 50),
            condition_tree=_normalize_json_field(r.get("condition_tree"), {}),
            action_type=r.get("action_type", "PLACE_ORDER"),
            action_params=_normalize_json_field(r.get("action_params"), {}),
            policy=_normalize_json_field(r.get("policy"), {"repeatable": True}),
            is_active=True,
        )



@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def add_algo(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        name = (request.POST.get("AlgoName") or "").strip()
        fund = (request.POST.get("Minimum_Fund_Reqd") or "").strip()
        desc = (request.POST.get("Algo_description") or "").strip()

        if not name:
            messages.error(request, "Algo name is required.")
            return redirect("add_algo")

        algo = AlgoList.objects.create(
            algo_name=name,
            minimum_fund_reqd=fund or None,
            algo_description=desc,
            created_by=request.user,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        # --- User Defined Variables (posted as user_variable_json_<idx>) ---
        for key, raw_json in request.POST.items():
            if not key.startswith("user_variable_json_"):
                continue
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                continue
            var_name = (data or {}).get("name")
            var_expr = (data or {}).get("expression")
            if var_name and isinstance(var_expr, list):
                # Avoid duplicates by (algo, user, name)
                if not UserDefinedVariable.objects.filter(algo=algo, user=request.user, name=var_name).exists():
                    UserDefinedVariable.objects.create(
                        algo=algo, user=request.user, name=var_name, expression=var_expr
                    )

        # --- Legs ---
        instruments       = request.POST.getlist("instrument_name[]")
        expiries          = request.POST.getlist("expiry_date[]")
        strikes           = request.POST.getlist("strike_price[]")
        order_directions  = request.POST.getlist("order_direction[]")
        order_types       = request.POST.getlist("order_type[]")
        option_types      = request.POST.getlist("option_type[]")
        exchange_segments = request.POST.getlist("exchange_segment[]")
        lot_qtys          = request.POST.getlist("lot_qty[]")
        lot_sizes         = request.POST.getlist("lot_size[]")
        strike_kinds      = request.POST.getlist("strike_kind[]")
        strike_targets    = request.POST.getlist("strike_target[]")
        sel_targets    = request.POST.getlist("strike_target_sel[]")
        custom_targets = request.POST.getlist("strike_target_custom[]")
        
        def normalized_target(i: int) -> str:
            sel = sel_targets[i] if i < len(sel_targets) else ""
            if sel == "__custom__":
                return (custom_targets[i] if i < len(custom_targets) else "").strip()
            return (sel or "").strip()
        legs = []
        n = len(instruments)
        for i in range(n):
            strike_kind = (strike_kinds[i] if i < len(strike_kinds) and strike_kinds[i] else 'ABS')
            strike_target_val = normalized_target(i) if strike_kind == 'OTM' else ''
            logic = AlgorithmLogic.objects.create(
                algo=algo,
                num_stocks=i + 1,
                instrument_name=instruments[i],
                expiry_date=expiries[i] if i < len(expiries) else "",
                strike_price=strikes[i] if i < len(strikes) else "",
                option_type=option_types[i] if i < len(option_types) else "",
                order_direction=order_directions[i] if i < len(order_directions) else "",
                order_type=order_types[i] if i < len(order_types) else "",
                exchange_segment=(exchange_segments[i] if i < len(exchange_segments) and exchange_segments[i] else "NFO"),
                lot_qty=int((lot_qtys[i] if i < len(lot_qtys) and lot_qtys[i] else "1")),
                lot_size_snapshot=(int(lot_sizes[i]) if i < len(lot_sizes) and lot_sizes[i] else None),
                strike_kind=strike_kind,
                strike_target=strike_target_val,
            )
            try:
                logic.full_clean()
            except ValidationError as e:
                messages.error(request, f"Leg {i+1} error: {e.message_dict}")
                raise  # stops tran
            legs.append(logic)
            # Entry conditions
        rules_json = request.POST.get("rules_json")
        print("RAW RULES_JSON from POST:", request.POST.get("rules_json"))
        _save_rules_for_algo(algo, legs, rules_json)
        messages.success(request, "✅ Algorithm created successfully")
        return redirect("algo_list")

    # --- GET ---
    segments_json, instruments_by_segment_json, symbol_list_json = build_instruments_context()
    variables = Variable.objects.prefetch_related("parameters").all()
    indicators_json = json.dumps([
        {
            "name": v.name,
            "display_name": v.display_name,
            "category": (v.category.name if getattr(v, "category", None) else "uncategorized"),
            "parameters": [
                {
                    "name": p.name,
                    "input_type": p.input_type,
                    "default_value": p.default_value,
                    "source_model": p.source_model,
                    "source_field": p.source_field,
                    "description": p.description,
                } for p in v.parameters.all()
            ],
        } for v in variables
    ], cls=DjangoJSONEncoder)

    # no algo yet, so empty UDVs
    user_vars_json = json.dumps([], cls=DjangoJSONEncoder)

    return render(request, "algorelated/add_algo.html", {
        # expose exactly what JS expects
        "segments": mark_safe(segments_json),
        "instruments_by_segment_json": mark_safe(instruments_by_segment_json),
        "symbol_list_json": mark_safe(symbol_list_json),
        "indicators_json": mark_safe(indicators_json),
        "user_vars_json": mark_safe(user_vars_json),
    })

    

# ---------- Edit Algo ----------

@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def edit_algo(request: HttpRequest, id: int) -> HttpResponse:
    algo = get_object_or_404(AlgoList, id=id)

    if request.method == "POST":
        name = (request.POST.get("AlgoName") or "").strip()
        fund = (request.POST.get("Minimum_Fund_Reqd") or "").strip()
        desc = (request.POST.get("Algo_description") or "").strip()

        if not name:
            messages.error(request, "Algo name is required.")
            return redirect("edit_algo", id=id)

        # Update algo
        algo.algo_name = name
        algo.minimum_fund_reqd = fund or None
        algo.algo_description = desc
        algo.updated_at = timezone.now()
        algo.save()

        # Replace UDVs
        UserDefinedVariable.objects.filter(algo=algo, user=request.user).delete()
        for key, raw_json in request.POST.items():
            if not key.startswith("user_variable_json_"):
                continue
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                continue
            var_name = (data or {}).get("name")
            var_expr = (data or {}).get("expression")
            if var_name and isinstance(var_expr, list):
                UserDefinedVariable.objects.create(
                    algo=algo, user=request.user, name=var_name, expression=var_expr
                )

        # Replace legs
        AlgorithmLogic.objects.filter(algo=algo).delete()

        instruments       = request.POST.getlist("instrument_name[]")
        expiries          = request.POST.getlist("expiry_date[]")
        strikes           = request.POST.getlist("strike_price[]")
        order_directions  = request.POST.getlist("order_direction[]")
        order_types       = request.POST.getlist("order_type[]")
        option_types      = request.POST.getlist("option_type[]")
        exchange_segments = request.POST.getlist("exchange_segment[]")
        lot_qtys          = request.POST.getlist("lot_qty[]")
        lot_sizes         = request.POST.getlist("lot_size[]")
        strike_kinds      = request.POST.getlist("strike_kind[]")
        strike_targets    = request.POST.getlist("strike_target[]")
        sel_targets    = request.POST.getlist("strike_target_sel[]")
        custom_targets = request.POST.getlist("strike_target_custom[]")
        
        def normalized_target(i: int) -> str:
            sel = sel_targets[i] if i < len(sel_targets) else ""
            if sel == "__custom__":
                return (custom_targets[i] if i < len(custom_targets) else "").strip()
            return (sel or "").strip()
        legs=[]
        n = len(instruments)
        for i in range(n):
            strike_kind = (strike_kinds[i] if i < len(strike_kinds) and strike_kinds[i] else 'ABS')
            strike_target_val = normalized_target(i) if strike_kind == 'OTM' else ''
            logic = AlgorithmLogic.objects.create(
                algo=algo,
                num_stocks=i + 1,
                instrument_name=instruments[i],
                expiry_date=expiries[i] if i < len(expiries) else "",
                strike_price=strikes[i] if i < len(strikes) else "",
                option_type=option_types[i] if i < len(option_types) else "",
                order_direction=order_directions[i] if i < len(order_directions) else "",
                order_type=order_types[i] if i < len(order_types) else "",
                exchange_segment=(exchange_segments[i] if i < len(exchange_segments) and exchange_segments[i] else "NFO"),
                lot_qty=int((lot_qtys[i] if i < len(lot_qtys) and lot_qtys[i] else "1")),
                lot_size_snapshot=(int(lot_sizes[i]) if i < len(lot_sizes) and lot_sizes[i] else None),
                strike_kind=(strike_kinds[i] if i < len(strike_kinds) and strike_kinds[i] else "ABS"),
                strike_target=(strike_targets[i] if i < len(strike_targets) else "") or "",
            )
            logic.full_clean()
            legs.append(logic)
         # Entry conditions
        rules_json = request.POST.get("rules_json")
        print("RAW RULES_JSON from POST:", request.POST.get("rules_json"))
        _save_rules_for_algo(algo, legs, rules_json)
        messages.success(request, "✅ Algorithm created successfully")
        return redirect("algo_list")

    # --- GET (edit) ---
    segments_json, instruments_by_segment_json, symbol_list_json = build_instruments_context()

    # Indicators (same as add)
    variables = Variable.objects.prefetch_related("parameters").all()
    indicators_json = json.dumps([
        {
            "name": v.name,
            "display_name": v.display_name,
            "category": (v.category.name if getattr(v, "category", None) else "uncategorized"),
            "parameters": [
                {
                    "name": p.name,
                    "input_type": p.input_type,
                    "default_value": p.default_value,
                    "source_model": p.source_model,
                    "source_field": p.source_field,
                    "description": p.description,
                } for p in v.parameters.all()
            ],
        } for v in variables
    ], cls=DjangoJSONEncoder)

    # Existing UDVs
    user_variables = UserDefinedVariable.objects.filter(algo=algo, user=request.user)
    user_vars_json = json.dumps([
        {"name": v.name, "expression": v.expression} for v in user_variables
    ], cls=DjangoJSONEncoder)

    # Existing legs (for edit restore)
    logic_entries = AlgorithmLogic.objects.filter(algo=algo).order_by("num_stocks")
    legs_data = []
    for leg in logic_entries:
        legs_data.append({
            "num_stocks": leg.num_stocks,
            "exchange_segment": getattr(leg, "exchange_segment", "NFO"),
            "instrument_name": leg.instrument_name,
            "expiry_date": leg.expiry_date,
            "strike_price": leg.strike_price,
            "option_type": leg.option_type,
            "order_type": leg.order_type,
            "order_direction": leg.order_direction,
            "lot_qty": getattr(leg, "lot_qty", 1),
            "lot_size_snapshot": getattr(leg, "lot_size_snapshot", None),
            "strike_kind": getattr(leg, "strike_kind", "ABS"),
            "strike_target": getattr(leg, "strike_target", ""),
        })
    # Rules
    rules = []
    for r in algo.rules.all():
        rules.append({
            "id": r.id,
            "rule_id": r.rule_id,
            "rule_type": r.rule_type,
            "scope": r.scope,
            "trigger_event": r.trigger_event,
            "priority": r.priority,
            # ✅ ensure dict, not string
            "condition_tree": r.condition_tree if isinstance(r.condition_tree, dict) else json.loads(r.condition_tree or "{}"),
            "action_type": r.action_type,
            "action_params": r.action_params if isinstance(r.action_params, dict) else json.loads(r.action_params or "{}"),
            "policy": r.policy if isinstance(r.policy, dict) else json.loads(r.policy or "{}"),
            "leg_id": r.leg_id,
            })
    
    
    return render(request, "algorelated/edit_algo.html", {
        "algo": algo,
        "is_edit_mode": True,

        # JS data blobs your frontend expects
        "segments": mark_safe(segments_json),
        "instruments_by_segment_json": mark_safe(instruments_by_segment_json),
        "symbol_list_json": mark_safe(symbol_list_json),

        "indicators_json": mark_safe(indicators_json),
        "user_vars_json": mark_safe(user_vars_json),
        "legs_json": legs_data,
        "rules_json": rules,
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


#--------------------------Algo Market place addded on 17/8/2025------#
# views.py
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponseBadRequest
import  datetime

@require_GET
@login_required
def market_offers_list(request):
    """
    Return offers discoverable for the user:
    - public active
    - unlisted/private only if user owns or has entitlement
    """
    q = request.GET.get("q","").strip().lower()
    rows = (AlgoOffer.objects
            .select_related("algo_list","owner")
            .filter(status="active")
            .exclude(visibility="private"))
    # simple search
    if q:
        rows = rows.filter(title__icontains=q)
    data=[]
    for o in rows:
        data.append({
            "id": o.id,
            "title": o.title,
            "tagline": o.tagline,
            "visibility": o.visibility,
            "owner": o.owner_id,
            "algo_list_id": o.algo_list_id,
            "plans": [{"id":p.id,"name":p.name,"period":p.period,"price_minor":p.price_minor,"currency":p.currency} for p in o.plans.filter(is_active=True)],
            "preview_stats": o.preview_stats,
        })
    return JsonResponse({"success": True, "offers": data})


@require_GET
@login_required
def market_offer_detail(request, offer_id):
    o = get_object_or_404(AlgoOffer.objects.select_related("algo_list","owner"), id=offer_id, status="active")
    return JsonResponse({
        "success": True,
        "offer": {
            "id": o.id, "title": o.title, "tagline": o.tagline, "description": o.description,
            "visibility": o.visibility, "owner": o.owner_id, "algo_list_id": o.algo_list_id,
            "plans": [{"id":p.id,"name":p.name,"period":p.period,"price_minor":p.price_minor,"currency":p.currency,"trial_days":p.trial_days} for p in o.plans.filter(is_active=True)],
            "preview_stats": o.preview_stats,
        }
    })


@require_POST
@login_required
def market_offer_invite(request, offer_id):
    """
    Creator sends invite to email or user-id. Payload:
    { "invitee_user_id": optional<int>, "invitee_email": optional<str>,
      "plan_id": optional<int>, "message": "...",
      "discount_type": "percent|amount|none", "discount_val": 0-100 or minor, "trial_days": optional<int>, "expires_in_days": optional<int> }
    """
    o = get_object_or_404(AlgoOffer, id=offer_id, owner=request.user)
    body = json.loads(request.body or "{}")
    plan = None
    if body.get("plan_id"):
        plan = get_object_or_404(AlgoPlan, id=body["plan_id"], offer=o)
    expires_at = timezone.now() + datetime.timedelta(days=int(body.get("expires_in_days", 14)))

    inv = AlgoInvitation.objects.create(
        offer=o, plan=plan, inviter=request.user,
        invitee_id=body.get("invitee_user_id"),
        invitee_email=(body.get("invitee_email") or "").strip(),
        message=(body.get("message") or "")[:280],
        discount_type=body.get("discount_type","none"),
        discount_val=int(body.get("discount_val") or 0),
        trial_days=body.get("trial_days"),
        expires_at=expires_at
    )
    # TODO: send email with link f"{SITE_URL}/market/invite/{inv.token}/"
    return JsonResponse({"success": True, "token": inv.token})


@require_GET
@login_required
def market_invite_accept(request, token):
    inv = get_object_or_404(AlgoInvitation, token=token, is_revoked=False)
    if inv.expires_at and inv.expires_at < timezone.now():
        return HttpResponseBadRequest("Invite expired")

    # Pick plan: invite plan > default active plan
    plan = inv.plan or inv.offer.plans.filter(is_active=True).first()
    if not plan:
        return HttpResponseBadRequest("No active plan for this offer")

    # Create a trial or zero-price subscription immediately; otherwise, redirect to checkout
    trial_days = inv.trial_days if inv.trial_days is not None else (plan.trial_days or inv.offer.default_trial_days if inv.offer.allow_trial else 0)
    now = timezone.now()
    sub, created = AlgoSubscription.objects.get_or_create(
        subscriber=request.user, offer=inv.offer, defaults={"plan": plan}
    )
    sub.plan = plan
    if trial_days > 0:
        sub.status = "trialing"
        sub.started_at = now
        sub.current_period_end = now + datetime.timedelta(days=trial_days)
    else:
        # If zero price -> activate; else caller should go through /market/subscribe
        if plan.price_minor == 0:
            sub.status = "active"
            sub.started_at = now
            sub.current_period_end = now + _period_delta(plan.period)
        else:
            sub.status = "past_due"
    sub.invitation = inv
    sub.save()

    inv.redeemed_at = now
    inv.save(update_fields=["redeemed_at"])

    # Entitlements will be rebuilt by signal
    return redirect('market_offer', offer_id=inv.offer_id)


# views.py (add near other imports)
import hmac, hashlib
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from core.models import (
    Invoice, CreatorEarning,WebhookEvent
)
from core.services.billing import compute_invoice_breakdown


def _period_delta(period: str) -> datetime.timedelta:
    p = (period or "").lower()
    if p == "monthly":
        return datetime.timedelta(days=30)
    if p == "quarterly":
        return datetime.timedelta(days=90)
    if p == "yearly":
        return datetime.timedelta(days=365)
    return datetime.timedelta(days=30)


def _parse_iso(ts: str) -> datetime.datetime:
    """
    Provider timestamps vary; be defensive.
    Return timezone-aware dt in UTC converted to settings TIME_ZONE.
    """
    if not ts:
        return timezone.now()
    try:
        # try unix seconds
        if isinstance(ts, (int, float)):
            return timezone.make_aware(datetime.datetime.utcfromtimestamp(ts))
        # try ISO
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(timezone.get_current_timezone())
    except Exception:
        return timezone.now()


def _verify_razorpay_signature(raw_body: bytes, signature: str) -> bool:
    """
    Verify Razorpay webhook signature using either SDK or HMAC fallback.
    """
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None)
    if not secret:
        return False
    # Prefer SDK if available
    try:
        import razorpay  # type: ignore
        razorpay.Utility.verify_webhook_signature(raw_body.decode("utf-8"), signature, secret)
        return True
    except Exception:
        # fallback manual HMAC
        try:
            mac = hmac.new(bytes(secret, "utf-8"), msg=raw_body, digestmod=hashlib.sha256).hexdigest()
            return hmac.compare_digest(mac, signature)
        except Exception:
            return False


def _verify_stripe_signature(raw_body: bytes, signature: str):
    """
    Verify Stripe webhook signature if stripe SDK available.
    Returns event dict if OK; raises on failure.
    """
    import importlib
    stripe = importlib.import_module("stripe")  # will raise if not installed
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
    if not endpoint_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET not set")
    return stripe.Webhook.construct_event(
        payload=raw_body, sig_header=signature, secret=endpoint_secret
    )



@require_POST
@login_required
def market_subscribe(request):
    """
    Payload: { "offer_id": int, "plan_id": int }
    If plan price==0 or user is in trial, immediately activate;
    otherwise return {checkout_url: "..."} for payment provider.
    """
    body = json.loads(request.body or "{}")
    offer = get_object_or_404(AlgoOffer, id=body.get("offer_id"), status="active")
    plan  = get_object_or_404(AlgoPlan, id=body.get("plan_id"), offer=offer, is_active=True)

    sub, _ = AlgoSubscription.objects.get_or_create(subscriber=request.user, offer=offer, defaults={"plan":plan})
    sub.plan = plan
    now = timezone.now()

    if plan.price_minor == 0:
        sub.status = "active"
        sub.started_at = now
        sub.current_period_end = now + _period_delta(plan.period)
        sub.save()
        return JsonResponse({"success": True, "activated": True})

    # TODO: create checkout session (Razorpay/Stripe). Stub:
    checkout_url = f"/checkout/start?offer={offer.id}&plan={plan.id}"
    sub.status = "past_due"
    sub.save()
    return JsonResponse({"success": True, "checkout_url": checkout_url})


# views.py (imports – keep your existing ones; add WebhookEvent and logging)

import logging
log = logging.getLogger("payments")


# --- Idempotency helpers ---
def _already_processed(provider: str, event_id: str) -> bool:
    if not event_id:
        return False
    return WebhookEvent.objects.filter(provider=provider, event_id=event_id).exists()

def _mark_processed(provider: str, event_id: str, payload: dict):
    if event_id:
        WebhookEvent.objects.get_or_create(provider=provider, event_id=event_id, defaults={"raw": payload})


@transaction.atomic
def _process_subscription_payment(*, provider: str, provider_sub_id: str,
                                  amount_minor: int, currency: str,
                                  event_time: datetime.datetime,
                                  meta: dict | None = None) -> JsonResponse:
    """
    Activate/extend subscription, create Invoice + CreatorEarning.
    """
    if not provider_sub_id:
        return JsonResponse({"ok": False, "error": "Missing provider_sub_id"}, status=400)

    sub = (AlgoSubscription.objects
           .select_related("offer", "plan", "subscriber")
           .filter(provider_sub_id=provider_sub_id)
           .first())
    if not sub:
        return JsonResponse({"ok": True, "skipped": "subscription_not_found"})

    # idempotency by timestamp as a secondary guard (primary is event-id in webhook)
    if sub.last_payment_at and sub.last_payment_at >= event_time:
        return JsonResponse({"ok": True, "skipped": "duplicate_or_old_event"})

    currency = currency or getattr(sub.plan, "currency", "INR")

    # What list price to show on invoice:
    list_price_minor = sub.plan.price_minor
    # The provider-charged amount is 'amount_minor' (final after discounts/taxes per provider)
    # We'll compute discount from meta if any.
    applied_discount_minor = 0
    if meta:
        applied_discount_minor = int(meta.get("discount_minor", 0) or 0)

    # Activate subscription and roll period
    now = timezone.now()
    next_end = now + _period_delta(sub.plan.period)

    sub.payment_provider = provider
    sub.status = "active"
    sub.last_payment_at = event_time or now
    sub.started_at = sub.started_at or now
    sub.current_period_end = next_end
    sub.save()

    bd = compute_invoice_breakdown(
        offer=sub.offer,
        list_price_minor=int(list_price_minor),
        discount_minor=int(max(0, applied_discount_minor))
    )

    inv = Invoice.objects.create(
        user=sub.subscriber, offer=sub.offer, subscription=sub,
        currency=currency,
        gross_minor=bd["gross"], discount_minor=bd["discount"], net_minor=bd["net"],
        platform_fee_pct=bd["platform_fee_pct"], platform_fee_minor=bd["platform_fee"],
        creator_gross_minor=bd["creator_gross"],
        gst_pct=bd["gst_pct"], gst_minor=bd["gst"],
        tds_pct=bd["tds_pct"], tds_minor=bd["tds"],
        creator_payout_minor=bd["creator_payout"],
        status="paid",
        issued_at=event_time or now
    )

    CreatorEarning.objects.create(
        creator=sub.offer.owner, invoice=inv, offer=sub.offer,
        amount_minor=bd["creator_payout"]
    )

    log.info("Subscription activated",
             extra={"provider": provider, "sub_id": provider_sub_id, "amount_minor": amount_minor,
                    "discount_minor": applied_discount_minor, "currency": currency})

    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def payments_webhook(request):
    """
    Unified webhook for Razorpay & Stripe with idempotency & discounts.
    """
    raw = request.body or b""

    # ---------- Razorpay ----------
    rz_sig = request.headers.get("X-Razorpay-Signature")
    if rz_sig:
        if not _verify_razorpay_signature(raw, rz_sig):
            return HttpResponseBadRequest("Invalid Razorpay signature")

        payload = json.loads(raw.decode("utf-8"))
        event = payload.get("event", "")
        data = payload.get("payload", {}) or {}

        # Build a stable event_id for idempotency
        candidate_ids = []
        try:
            if "payment" in data and data["payment"].get("entity"):
                candidate_ids.append(data["payment"]["entity"].get("id"))
            if "invoice" in data and data["invoice"].get("entity"):
                candidate_ids.append(data["invoice"]["entity"].get("id"))
            if "subscription" in data and data["subscription"].get("entity"):
                candidate_ids.append(data["subscription"]["entity"].get("id"))
        except Exception:
            pass
        base = event or "rz_event"
        core_id = next((x for x in candidate_ids if x), "")
        event_id = f"{base}:{core_id}"

        if _already_processed("razorpay", event_id):
            return JsonResponse({"ok": True, "skipped": "duplicate_event"})

        # Extract sub_id, amount, currency, time
        sub_id = None
        amount_paid = None
        currency = "INR"
        event_time = _parse_iso(payload.get("created_at"))

        notes = {}
        try:
            if "subscription" in data and data["subscription"].get("entity"):
                ent = data["subscription"]["entity"]
                sub_id = ent.get("id") or sub_id

            if "payment" in data and data["payment"].get("entity"):
                p = data["payment"]["entity"]
                sub_id = p.get("subscription_id") or sub_id
                amount_paid = p.get("amount")
                currency = p.get("currency") or currency
                event_time = _parse_iso(p.get("created_at"))
                notes = p.get("notes") or notes

            if "invoice" in data and data["invoice"].get("entity"):
                inv = data["invoice"]["entity"]
                sub_id = inv.get("subscription_id") or sub_id
                amount_paid = inv.get("amount_paid") or inv.get("amount_due") or amount_paid
                currency = inv.get("currency") or currency
                event_time = _parse_iso(inv.get("created_at"))
                notes = inv.get("notes") or notes
        except Exception:
            pass

        # Derive discount:
        # Preferred: explicit notes.discount_minor (you can set this during checkout/session creation)
        discount_minor = 0
        try:
            if isinstance(notes, dict):
                if "discount_minor" in notes:
                    discount_minor = int(notes.get("discount_minor") or 0)
                else:
                    # Fallback: if you passed list_price_minor in notes, compute discount = list_price_minor - amount_paid
                    if "list_price_minor" in notes and amount_paid is not None:
                        discount_minor = max(0, int(notes["list_price_minor"]) - int(amount_paid))
        except Exception:
            discount_minor = 0

        resp = _process_subscription_payment(
            provider="razorpay",
            provider_sub_id=sub_id or "",
            amount_minor=int(amount_paid or 0),
            currency=currency,
            event_time=event_time,
            meta={"event": event, "discount_minor": discount_minor}
        )
        _mark_processed("razorpay", event_id, payload)
        return resp

    # ---------- Stripe ----------
    st_sig = request.headers.get("Stripe-Signature")
    if st_sig:
        try:
            event = _verify_stripe_signature(raw, st_sig)
        except Exception as e:
            return HttpResponseBadRequest(f"Invalid Stripe signature: {e}")

        etype = event["type"]
        event_id = event["id"]

        if _already_processed("stripe", event_id):
            return JsonResponse({"ok": True, "skipped": "duplicate_event"})

        obj = event["data"]["object"]
        sub_id = None
        amount_paid = None
        currency = None
        event_time = timezone.now()
        discount_minor = 0

        if etype == "invoice.paid":
            # object = invoice
            sub_id = obj.get("subscription")
            amount_paid = obj.get("amount_paid")  # cents
            currency = (obj.get("currency") or "").upper()
            # Stripe discount sources:
            tda = obj.get("total_discount_amounts") or []
            if isinstance(tda, list):
                discount_minor = sum(int(x.get("amount") or 0) for x in tda)
            if not discount_minor:
                subtotal = obj.get("subtotal")
                total = obj.get("total")
                if subtotal is not None and total is not None and subtotal >= total:
                    discount_minor = int(subtotal) - int(total)
            event_time = _parse_iso(obj.get("status_transitions", {}).get("paid_at") or obj.get("created"))

        elif etype in ("customer.subscription.created", "customer.subscription.updated"):
            # We only activate on invoice.paid to ensure money moved
            _mark_processed("stripe", event_id, event.to_dict() if hasattr(event, "to_dict") else event)
            return JsonResponse({"ok": True, "skipped": etype})

        if not sub_id:
            _mark_processed("stripe", event_id, event.to_dict() if hasattr(event, "to_dict") else event)
            return JsonResponse({"ok": True, "skipped": "no_subscription_id"})

        resp = _process_subscription_payment(
            provider="stripe",
            provider_sub_id=sub_id,
            amount_minor=int(amount_paid or 0),
            currency=currency or "USD",
            event_time=event_time,
            meta={"event": etype, "discount_minor": int(discount_minor or 0)}
        )
        _mark_processed("stripe", event_id, event.to_dict() if hasattr(event, "to_dict") else event)
        return resp

    # Unknown provider
    return HttpResponse(status=204)
# views.py (add near other imports at top)

# ---- helper: map our plan.period -> provider period ----
def _razorpay_period(plan_period: str) -> str:
    # our: monthly/quarterly/yearly -> razorpay: daily, weekly, monthly, yearly
    p = (plan_period or "").lower()
    return {"monthly":"monthly", "quarterly":"yearly", "yearly":"yearly"}.get(p, "monthly")

def _stripe_interval(plan_period: str) -> dict:
    p = (plan_period or "").lower()
    if p == "monthly":   return {"interval": "month", "interval_count": 1}
    if p == "quarterly": return {"interval": "month", "interval_count": 3}
    if p == "yearly":    return {"interval": "year",  "interval_count": 1}
    return {"interval": "month", "interval_count": 1}

@csrf_exempt
@require_POST
@login_required
def checkout_start(request):
    """
    POST JSON: { "offer_id": int, "plan_id": int, "provider": "razorpay"|"stripe", "discount_minor": 0 }
    Returns provider-specific checkout data.
    - For Razorpay: creates a Subscription and returns {subscription_id, short_url?}
    - For Stripe:   creates a Checkout Session and returns {checkout_url}
    Also sets 'notes': {list_price_minor, discount_minor} so the webhook can compute invoice discounts.
    """
    try:
        body = json.loads(request.body or "{}")
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    offer = get_object_or_404(AlgoOffer, id=body.get("offer_id"), status="active")
    plan  = get_object_or_404(AlgoPlan, id=body.get("plan_id"), offer=offer, is_active=True)

    provider = (body.get("provider") or "").lower()
    if not provider:
        provider = "razorpay" if getattr(settings, "RAZORPAY_KEY_ID", None) else "stripe"

    discount_minor = int(body.get("discount_minor") or 0)
    list_price_minor = int(plan.price_minor or 0)

    # Ensure we have or create a local subscription row (we’ll set provider ids after creating checkout)
    sub, _ = AlgoSubscription.objects.get_or_create(subscriber=request.user, offer=offer, defaults={"plan": plan})
    sub.plan = plan
    sub.status = "past_due"  # will flip to 'active' on webhook payment confirmation
    sub.save()

    # ---------- Razorpay ----------
    if provider == "razorpay":
        key_id     = getattr(settings, "RAZORPAY_KEY_ID", None)
        key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", None)
        if not (key_id and key_secret):
            return JsonResponse({"success": False, "error": "Razorpay keys not configured"}, status=400)

        # lazy import
        try:
            import razorpay  # type: ignore
        except Exception as e:
            return JsonResponse({"success": False, "error": f"razorpay package missing: {e}"}, status=400)

        client = razorpay.Client(auth=(key_id, key_secret))

        # 1) Ensure a Razorpay Plan exists (or reuse)
        if not plan.provider_plan_id:
            rzp_period = _razorpay_period(plan.period)
            # Razorpay plan amount is minor units; we set currency & period; notes optional
            rp = client.plan.create({
                "period": rzp_period,
                "interval": 1 if plan.period != "quarterly" else 3,  # quarterly = every 3 months
                "item": {
                    "name": f"{offer.title} - {plan.name}",
                    "amount": list_price_minor,
                    "currency": plan.currency or "INR"
                }
            })
            plan.provider = "razorpay"
            plan.provider_plan_id = rp["id"]
            plan.save(update_fields=["provider", "provider_plan_id"])

        # 2) Create Razorpay Subscription
        # notes are IMPORTANT: webhook will use these to compute discount
        notes = {"list_price_minor": list_price_minor}
        if discount_minor > 0:
            notes["discount_minor"] = discount_minor

        # total_count: how many periods to charge before auto-cancel; keep None/Open for continuous billing
        sub_payload = {
            "plan_id": plan.provider_plan_id,
            "customer_notify": 1,
            "total_count": None,  # continuous; set an integer if you want fixed cycles
            "notes": notes
        }
        rz_sub = client.subscription.create(sub_payload)

        # Store provider ids on our subscription
        sub.payment_provider = "razorpay"
        sub.provider_sub_id  = rz_sub["id"]
        sub.save(update_fields=["payment_provider", "provider_sub_id"])

        # If you use Razorpay Payment Links or Subscription Short URL, return it here (if present)
        short_url = rz_sub.get("short_url") or ""
        return JsonResponse({
            "success": True,
            "provider": "razorpay",
            "subscription_id": rz_sub["id"],
            "short_url": short_url
        })

    # ---------- Stripe ----------
    elif provider == "stripe":
        # You should have created Stripe Prices in the dashboard; store price id on AlgoPlan
        price_id = plan.stripe_price_id
        if not price_id:
            return JsonResponse({"success": False, "error": "Stripe price_id not configured on plan"}, status=400)

        try:
            import stripe  # type: ignore
        except Exception as e:
            return JsonResponse({"success": False, "error": f"stripe package missing: {e}"}, status=400)

        stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)
        if not stripe.api_key:
            return JsonResponse({"success": False, "error": "STRIPE_SECRET_KEY not configured"}, status=400)

        # Create a Checkout Session for subscription
        # NOTE: Discounts in Stripe are better handled via coupons/promotion codes.
        # For parity with Razorpay 'notes', we can pass metadata with list_price/discount.
        metadata = {
            "offer_id": str(offer.id),
            "plan_id": str(plan.id),
            "list_price_minor": str(list_price_minor),
            "discount_minor": str(discount_minor)
        }

        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=getattr(settings, "CHECKOUT_SUCCESS_URL", "https://example.com/success"),
            cancel_url=getattr(settings, "CHECKOUT_CANCEL_URL", "https://example.com/cancel"),
            metadata=metadata,
            allow_promotion_codes=True
        )

        # Store the provider_sub_id only after webhook invoice.paid (Stripe gives it post-payment),
        # but we can store the session id for tracking if you want:
        # sub.provider_sub_id will be set by webhook using event.data.object.subscription

        sub.payment_provider = "stripe"
        sub.save(update_fields=["payment_provider"])

        return JsonResponse({
            "success": True,
            "provider": "stripe",
            "checkout_url": session.url
        })

    else:
        return JsonResponse({"success": False, "error": "Unknown provider"}, status=400)

#-----performance apis------

# --- Performance helpers (pure Python, no external deps) ---
import math

def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0

def _stddev(xs):
    xs = list(xs)
    n = len(xs)
    if n < 2:
        return 0.0
    mu = _mean(xs)
    var = sum((x - mu) ** 2 for x in xs) / (n - 1)  # sample std
    return math.sqrt(var)

def _max_drawdown(equity_curve):
    """
    equity_curve: list of floats (cumulative equity, e.g., starting at 1.0)
    Returns drawdown as a negative fraction, e.g., -0.18 for -18%.
    """
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    mdd = 0.0  # negative
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (v / peak) - 1.0
        if dd < mdd:
            mdd = dd
    return mdd

def _annualize_sharpe(daily_returns):
    """
    daily_returns: list of daily return fractions, e.g., 0.001 = 0.1%
    Sharpe = (mean / std) * sqrt(252)
    """
    if not daily_returns:
        return None
    mu = _mean(daily_returns)
    sd = _stddev(daily_returns)
    if sd == 0:
        return None
    return (mu / sd) * math.sqrt(252)

def _cagr_from_equity(equity_curve, start_date, end_date):
    """
    equity_curve: list of equity multipliers (start near 1.0), strictly positive.
    Returns CAGR as fraction (0.22 = 22%).
    """
    if not equity_curve or equity_curve[0] <= 0:
        return None
    start_val = equity_curve[0]
    end_val = equity_curve[-1]
    if end_date <= start_date or start_val <= 0:
        return None
    days = (end_date - start_date).days or 1
    years = days / 365.0
    if years <= 0:
        return None
    if end_val <= 0:
        return None
    try:
        return (end_val / start_val) ** (1.0 / years) - 1.0
    except Exception:
        return None


# ---------------- Performance API ----------------
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

@require_GET
@login_required
def api_algo_performance(request):
    """
    GET /api/algo/performance?algo_id=123&days=30&mode=all&capital=100000
    Returns:
    {
      "series": [{"date":"YYYY-MM-DD","pnl": float}, ...],
      "sharpe": float|null,
      "mdd": float|null,       # -0.18 for -18%
      "win_rate": float|null,  # 0.57 for 57%
      "cagr": float|null       # 0.24 for 24%
    }
    Notes:
      - Uses DailyPnl rows for the current user and algo_id
      - daily return = pnl / capital (default 100,000)
      - equity curve = cumulative (1 + returns)
    """
    try:
        algo_id = int(request.GET.get("algo_id"))
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid or missing algo_id"}, status=400)

    try:
        days = int(request.GET.get("days", 30))
        days = max(1, min(days, 3650))  # cap to 10 years
    except ValueError:
        days = 30

    mode = (request.GET.get("mode") or "all").lower()
    try:
        capital = float(request.GET.get("capital", 100000))
        if capital <= 0:
            capital = 100000.0
    except ValueError:
        capital = 100000.0

    since = timezone.now().date() - timedelta(days=days - 1)

    qs = DailyPnl.objects.filter(user=request.user, algo_id=algo_id, date__gte=since)
    if mode in ("paper", "live"):
        qs = qs.filter(mode=mode)

    # Order by date ascending
    rows = list(qs.order_by("date").values("date", "pnl"))

    # Build series for JSON (use floats)
    series = [{"date": r["date"].isoformat(), "pnl": float(r["pnl"] or 0.0)} for r in rows]

    # Compute metrics
    daily_returns = [ (float(r["pnl"] or 0.0) / capital) for r in rows ]
    if series:
        start_date = rows[0]["date"]
        end_date   = rows[-1]["date"]
    else:
        start_date = timezone.now().date()
        end_date   = start_date

    # equity as multiplier starting at 1.0
    equity = []
    acc = 1.0
    for ret in daily_returns:
        acc *= (1.0 + ret)
        equity.append(acc)

    sharpe = _annualize_sharpe(daily_returns)
    mdd = _max_drawdown(equity) if equity else None
    wins = sum(1 for r in daily_returns if r > 0)
    total_days = len(daily_returns)
    win_rate = (wins / total_days) if total_days > 0 else None
    cagr = _cagr_from_equity(equity, start_date, end_date) if equity else None

    return JsonResponse({
        "success": True,
        "series": series,
        "sharpe": None if sharpe is None else round(sharpe, 3),
        "mdd":    None if mdd    is None else round(mdd, 4),
        "win_rate": None if win_rate is None else round(win_rate, 4),
        "cagr":     None if cagr     is None else round(cagr, 4),
    })
#-----------------some edits on 19/08/2025-------#
# --- Hidden algos (session-backed, no migrations required) ---
from django.views.decorators.http import require_http_methods

SESSION_HIDDEN_KEY = "dashboard_hidden_algos"

def _get_hidden_set(request):
    try:
        ids = request.session.get(SESSION_HIDDEN_KEY, [])
        # normalize to strings to avoid type issues in JS
        return set(str(x) for x in ids if x is not None)
    except Exception:
        return set()

def _save_hidden_set(request, s):
    request.session[SESSION_HIDDEN_KEY] = list(s)
    request.session.modified = True

@csrf_exempt
@login_required
@require_http_methods(["GET", "POST"])
def api_dashboard_toggle_hide(request):
    """
    GET  -> {success: true, hidden: [ "12","34", ... ] }  // current hidden list
    POST -> body: {"algo_list_id": 123, "hide": true|false}
            returns same payload
    """
    if request.method == "GET":
        hidden = sorted(_get_hidden_set(request))
        return JsonResponse({"success": True, "hidden": hidden})

    # POST
    try:
        body = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    algo_id = body.get("algo_list_id")
    hide = body.get("hide")
    if algo_id is None or hide is None:
        return JsonResponse({"success": False, "error": "algo_list_id and hide required"}, status=400)

    s = _get_hidden_set(request)
    key = str(algo_id)
    if bool(hide):
        s.add(key)
    else:
        s.discard(key)
    _save_hidden_set(request, s)
    return JsonResponse({"success": True, "hidden": sorted(s)})

@login_required
def marketplace_page(request):
    return render(request, "marketplace.html")

@login_required
@require_http_methods(["POST"])
def delete_account(request):
    mode = (request.POST.get("mode") or "").strip()   # "password" | "otp"
    if mode == "password":
        cur = request.POST.get("current_password") or ""
        if not request.user.check_password(cur):
            return JsonResponse({"ok":False,"error":"Current password is incorrect."}, status=400)
    elif mode == "otp":
        email_code = (request.POST.get("email_code") or "").strip()
        phone_code = (request.POST.get("phone_code") or "").strip()
        now = timezone.now()
        if request.user.email:
            ok = PendingContactChange.objects.filter(
                user=request.user, field="email", new_value=request.user.email,
                code=email_code, expires_at__gte=now
            ).exists()
            if not ok:
                return JsonResponse({"ok":False,"error":"Email OTP invalid or expired."}, status=400)
        if request.user.phone:
            ok = PendingContactChange.objects.filter(
                user=request.user, field="phone", new_value=request.user.phone,
                code=phone_code, expires_at__gte=now
            ).exists()
            if not ok:
                return JsonResponse({"ok":False,"error":"Phone OTP invalid or expired."}, status=400)
        PendingContactChange.objects.filter(user=request.user, field__in=["email","phone"]).delete()
    else:
        return JsonResponse({"ok":False,"error":"Invalid mode."}, status=400)

    # Perform deletion (optionally soft-delete)
    u = request.user
    from django.contrib.auth import logout as auth_logout
    auth_logout(request)
    u.delete()
    return JsonResponse({"ok":True})

# views.py

from .models import Exchange, BrokerExchangeMap  # import new models

@login_required
@require_http_methods(["GET"])
def broker_edit_page(request, broker_id):
    broker = get_object_or_404(Broker, id=broker_id)
    return render(request, "accounts/edit_broker.html", {"broker": broker})  # template below

@login_required
@require_http_methods(["GET"])
def api_brokers(request):
    data = [{
        "id": b.id,
        "broker_name": b.broker_name,
        "root_api": b.root_api,
        "adapter_path": b.adapter_path or "",
    } for b in Broker.objects.all().order_by("broker_name")]
    return JsonResponse({"success": True, "brokers": data})

@login_required
@require_http_methods(["GET"])
def api_exchanges(request):
    rows = Exchange.objects.filter(is_active=True).order_by("key").values(
        "id","key","name","segment_kind","default_xts_segment"
    )
    return JsonResponse({"success": True, "exchanges": list(rows)})

@csrf_exempt
@login_required
def api_broker_detail(request, broker_id):
    broker = get_object_or_404(Broker, id=broker_id)

    if request.method == "GET":
        # broker basics
        out = {
            "id": broker.id,
            "broker_name": broker.broker_name,
            "root_api": broker.root_api,
            "server_ip": broker.server_ip,
            "adapter_path": broker.adapter_path,
        }
        # current mappings
        maps = (BrokerExchangeMap.objects
                .filter(broker=broker)
                .select_related("exchange")
                .order_by("exchange__key"))
        mapped = [{
            "exchange_id": m.exchange_id,
            "exchange_key": m.exchange.key,
            "broker_code" : m.broker_code,
            "xts_segment" : m.xts_segment,
        } for m in maps]
        return JsonResponse({"success": True, "broker": out, "mappings": mapped})

    if request.method == "POST":
        try:
            body = json.loads(request.body or "{}")
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Invalid JSON: {e}"}, status=400)

        # update basics (optional)
        for f in ["broker_name","root_api","server_ip","adapter_path"]:
            if f in body:
                setattr(broker, f, (body.get(f) or "").strip() or None)
        broker.save()

        # upsert mappings: expect [{exchange_id, broker_code, xts_segment?}, ...]
        rows = body.get("mappings") or []
        if not isinstance(rows, list):
            return JsonResponse({"success": False, "error": "mappings must be a list"}, status=400)

        seen_pairs = set()
        for r in rows:
            try:
                ex_id = int(r.get("exchange_id"))
                broker_code = (r.get("broker_code") or "").strip()
                xts_segment = r.get("xts_segment", None)
                if xts_segment in ("", None): xts_segment = None
                else: xts_segment = int(xts_segment)
            except Exception:
                return JsonResponse({"success": False, "error": "Bad mapping row"}, status=400)

            if not broker_code:
                continue
            ex = get_object_or_404(Exchange, id=ex_id)
            obj, _ = BrokerExchangeMap.objects.update_or_create(
                broker=broker, exchange=ex,
                defaults={"broker_code": broker_code, "xts_segment": xts_segment}
            )
            seen_pairs.add((broker.id, ex.id))

        # delete any mapping not present in payload
        BrokerExchangeMap.objects.filter(broker=broker).exclude(
            exchange_id__in=[ex for (_b, ex) in seen_pairs]
        ).delete()

        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Invalid method"}, status=405)
