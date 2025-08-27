from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db.models import Q, UniqueConstraint
from django.utils import timezone
import uuid
from django.utils.crypto import get_random_string
from django.core.validators import RegexValidator  # ADD THIS
import random
import string
import logging
from django.core.validators import MinValueValidator

class AlgoRule(models.Model):
    algo = models.ForeignKey("AlgoList", on_delete=models.CASCADE, related_name="rules")
    leg = models.ForeignKey("AlgorithmLogic", on_delete=models.CASCADE, null=True, blank=True)
    rule_id = models.CharField(max_length=36)
    rule_type = models.CharField(max_length=20) # RuleType
    scope = models.CharField(max_length=20) # Scope
    trigger_event = models.CharField(max_length=20) # TriggerEvent
    priority = models.IntegerField(default=50)
# Serialized condition tree from builder (your existing nested AND/OR JSON)
    condition_tree = models.JSONField(default=dict)
# Action envelope
    action_type = models.CharField(max_length=24) # ActionType
    action_params = models.JSONField(default=dict)
# Policy
    policy =models.JSONField(default=dict) # {repeatable, cooldown_seconds, max_fires_per_session, min_dwell_seconds, dependency, is_reentry, hysteresis}

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        indexes = [
            models.Index(fields=["algo", "priority"]),
            models.Index(fields=["algo", "rule_type"]),
            ]

log = logging.getLogger(__name__)
# models.py (near imports)


def pending_signup_token():
    return uuid.uuid4().hex

def invite_token():
    return get_random_string(32)

def offer_logo_upload(instance, filename):
    return f"offers/{instance.owner_id}/{filename}"

class AlgoStatusStyle(models.Model):
    """
    Optional theme map for dashboard statuses. If user is NULL → global default.
    User-specific rows override the global for that key.
    """
    STATUS_KEYS = [
        ('unregistered', 'Unregistered'),
        ('paper_ready',  'Paper Ready'),
        ('live_ready',   'Live Ready'),
        ('running',      'Running'),
        ('paused',       'Paused'),
        ('stopped',      'Stopped'),
        ('error',        'Error'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    key = models.CharField(max_length=24, choices=STATUS_KEYS)
    label = models.CharField(max_length=32, blank=True, default='')

    # Either use Bulma classes, or raw colors, or both.
    bulma_tag_class = models.CharField(max_length=64, blank=True, default='')  # e.g. "is-light"
    bulma_bg_class  = models.CharField(max_length=64, blank=True, default='')  # e.g. "has-background-success-light"

    dot_hex   = models.CharField(max_length=7, blank=True, default='')  # e.g. "#d4edda"
    text_hex  = models.CharField(max_length=7, blank=True, default='')  # e.g. "#155724"
    order     = models.PositiveIntegerField(default=100)                # optional sort

    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'key')
        ordering = ['order', 'key']

    def __str__(self):
        scope = f"user={self.user_id}" if self.user_id else "global"
        return f"{self.key} [{scope}]"

# models.py

from django.contrib.auth.hashers import make_password


class PendingSignup(models.Model):
    token = models.CharField(max_length=64, unique=True, default=pending_signup_token)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    password_hash = models.CharField(max_length=256)  # store hashed
    email_code = models.CharField(max_length=6)
    phone_code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def gen_code():
        return f"{random.randint(0, 999999):06d}"

    @classmethod
    def start(cls, *, email:str, phone:str, raw_password:str, ttl_seconds:int=600):
        now = timezone.now()
        return cls.objects.create(
            email=email.strip().lower(),
            phone=phone.strip(),
            password_hash=make_password(raw_password),
            email_code=cls.gen_code(),
            phone_code=cls.gen_code(),
            expires_at=now + timezone.timedelta(seconds=ttl_seconds),
        )

    def expired(self):
        return self.expires_at < timezone.now()
    
    
    
    # models.py
class PendingContactChange(models.Model):
    FIELD_CHOICES = (("email","Email"), ("phone","Phone"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pending_changes")
    field = models.CharField(max_length=10, choices=FIELD_CHOICES)
    new_value = models.CharField(max_length=255)
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def gen_code():
        return f"{random.randint(0, 999999):06d}"


class AlgoRun(models.Model):
    MODE_CHOICES = (('paper','Paper'), ('live','Live'))
    STATUS_CHOICES = (('stopped','Stopped'), ('running','Running'), ('paused','Paused'), ('error','Error'))

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    algo = models.ForeignKey('AlgorithmLogic', on_delete=models.CASCADE)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='paper')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='stopped')
    account = models.ForeignKey('BrokerAccount', on_delete=models.SET_NULL, null=True, blank=True)
    last_heartbeat = models.DateTimeField(blank=True, null=True)
    last_error = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user','algo','mode')

    def __str__(self):
        return f"{self.user_id}:{self.algo_id}:{self.mode}({self.status})"


class DailyPnl(models.Model):
    """
    Simple returns table (inserted by your executor/cron).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    algo = models.ForeignKey('AlgorithmLogic', on_delete=models.CASCADE)
    mode = models.CharField(max_length=10, choices=(('paper','Paper'), ('live','Live')))
    date = models.DateField()
    pnl = models.FloatField(default=0.0)
    cum_pnl = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('user','algo','mode','date')
        indexes = [models.Index(fields=['user','algo','mode','date'])]


class ExecutionLog(models.Model):
    """
    Recent runtime logs. Keep it small & indexed; rotate/cleanup via cron.
    """
    LEVELS = (('INFO','INFO'), ('WARN','WARN'), ('ERROR','ERROR'), ('DEBUG','DEBUG'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    algo = models.ForeignKey('AlgorithmLogic', on_delete=models.CASCADE)
    mode = models.CharField(max_length=10, choices=(('paper','Paper'), ('live','Live')))
    ts = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=LEVELS, default='INFO')
    message = models.TextField()

    class Meta:
        indexes = [models.Index(fields=['user','algo','mode','-ts'])]


class User(AbstractUser):
    name = models.CharField(max_length=1000)

    # NEW: phone with basic E.164-ish validation; keep nullable now to avoid breaking existing rows.
    phone = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        validators=[RegexValidator(r'^\+?\d{7,15}$', 'Enter a valid phone number.')]
    )

    # NEW: flags set after OTP verification
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    def __str__(self):
        # (optional) nicer display when username is blank
        return self.username or self.email or (self.phone or "")
class OTP(models.Model):
    PURPOSES = (
        ("signup", "Signup"),
        ("login", "Login"),
        ("reset", "Password Reset"),
    )
    CHANNELS = (("email", "Email"), ("phone", "Phone"))

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps")
    purpose = models.CharField(max_length=16, choices=PURPOSES)
    channel = models.CharField(max_length=8, choices=CHANNELS)

    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["user", "purpose", "channel", "expires_at"]),
        ]

    @staticmethod
    def generate_code():
        # 6-digit numeric code
        from random import randint
        return f"{randint(100000, 999999)}"

    @classmethod
    def create_otp(cls, user, purpose, channel, ttl_seconds=600):
        code = "".join(random.choices(string.digits, k=6))
        obj = cls.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            channel=channel,
            expires_at=timezone.now() + timezone.timedelta(seconds=ttl_seconds)
        )
        # 👇 dev-mode delivery
        print(f"[OTP] {channel} OTP for {user}: {code}")
        log.info("[OTP] %s OTP for %s: %s", channel, user, code)
        return obj
    @classmethod
    def create_dual_distinct(cls, user, purpose="verify", ttl_seconds=600):
       """Create two different codes: one for email, one for phone. Returns (email_code, phone_code)."""
       expires = timezone.now() + timezone.timedelta(seconds=ttl_seconds)
       email_code = phone_code = None

       if user.email:
           email_code = cls.generate_code()
           cls.objects.create(user=user, purpose=purpose, channel="email",
                              code=email_code, expires_at=expires, is_used=False)
           print(f"[OTP][{purpose.upper()}][EMAIL] {user.username} -> {email_code}")

       if user.phone:
           phone_code = cls.generate_code()
           # ensure distinct; tiny guard if RNG gave same value (very unlikely)
           if phone_code == email_code:
               phone_code = cls.generate_code()
           cls.objects.create(user=user, purpose=purpose, channel="phone",
                              code=phone_code, expires_at=expires, is_used=False)
           print(f"[OTP][{purpose.upper()}][PHONE] {user.username} -> {phone_code}")

       return email_code, phone_code
    # in models.py, inside class OTP:
    @classmethod
    def create_dual_login_otp(cls, user, ttl_seconds=600):
        code = cls.generate_code()
        expires = timezone.now() + timezone.timedelta(seconds=ttl_seconds)
        rows = []
        if user.email:
            rows.append(cls.objects.create(user=user, purpose="login", channel="email", code=code, expires_at=expires))
        if user.phone:
            rows.append(cls.objects.create(user=user, purpose="login", channel="phone", code=code, expires_at=expires))
        print(f"[OTP][LOGIN] for {user.username} ({user.email or ''} / {user.phone or ''}) -> {code}")
        return code, rows


    def is_valid(self, code: str) -> bool:
        return (
            not self.is_used and
            timezone.now() <= self.expires_at and
            self.code == code
        )


class Broker(models.Model):
    broker_name = models.CharField(max_length=100, unique=True)
    root_api = models.TextField()
    server_ip = models.TextField(blank=True, null=True)
    authenticator_req = models.IntegerField(blank=True, null=True)
    password_req = models.IntegerField(blank=True, null=True)
    adapter_path = models.CharField(  # ← NEW
        max_length=255, blank=True, null=True,
        help_text="Import path to adapter class, e.g. core.services.brokers.zerodha.ZerodhaClient"
    )
    def __str__(self):
        return self.broker_name

# models.py

class Exchange(models.Model):
    """
    Our canonical exchanges/segments.
    key: stable logical key used across the app (e.g. 'NSE_EQ', 'NFO_FO')
    """
    key = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=64)              # Human label: "NSE Equity"
    mic = models.CharField(max_length=16, blank=True)   # Optional, e.g. XNSE
    segment_kind = models.CharField(                    # Optional taxonomy
        max_length=16,
        choices=[("EQ","Equity"),("FO","F&O"),("CDS","Currency"),("COM","Commodity")],
        blank=True
    )
    default_xts_segment = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self): return f"{self.key} ({self.name})"


class BrokerExchangeMap(models.Model):
    """
    Per-broker mapping from our Exchange to the broker's code and (optional) XTS segment override.
    """
    broker = models.ForeignKey("Broker", on_delete=models.CASCADE, related_name="exchange_maps")
    exchange = models.ForeignKey("Exchange", on_delete=models.CASCADE, related_name="broker_maps")
    broker_code = models.CharField(max_length=32)              # e.g. 'NSE', 'NFO', 'MCX'
    xts_segment = models.IntegerField(null=True, blank=True)   # override if broker differs

    class Meta:
        unique_together = ("broker", "exchange")

    def __str__(self): return f"{self.broker.broker_name}:{self.exchange.key}→{self.broker_code}"

# You already have:
# class Broker(models.Model): ...

# If not already imported in this file:
# from .models import AlgorithmLogic   # adjust import path to where AlgorithmLogic lives


class BrokerAccount(models.Model):
    """
    Reusable broker login/config owned by a user; can be linked to many algos.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    broker = models.ForeignKey('Broker', on_delete=models.PROTECT)

    label = models.CharField(max_length=100)                 # human-friendly name e.g. "Zerodha Main"
    broker_username = models.CharField(max_length=255)       # the login/ID at the broker

    credentials = models.JSONField(default=dict, blank=True) # store api_key/secret/access_token/etc (encrypt in prod)
    is_active = models.BooleanField(default=True)

    last_test_at = models.DateTimeField(null=True, blank=True)
    last_test_ok = models.BooleanField(default=False)
    last_error = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['user', 'label'], name='uniq_brokeraccount_label_per_user'),
            UniqueConstraint(fields=['user', 'broker', 'broker_username'], name='uniq_real_account_per_user_broker'),
        ]
        indexes = [
            models.Index(fields=['user', 'broker']),
        ]

    def __str__(self):
        return f"{self.user.username} · {self.label} ({self.broker.broker_name})"


class AlgoBrokerLink(models.Model):
    """
    Link an algo to a BrokerAccount. Supports multiple accounts per algo (roles) and one default.
    """
    ROLE_CHOICES = (('primary', 'Primary'), ('hedge', 'Hedge'), ('paper', 'Paper'))

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    algo = models.ForeignKey('AlgorithmLogic', on_delete=models.CASCADE)
    account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='primary')
    is_default = models.BooleanField(default=False)
    settings = models.JSONField(default=dict, blank=True)  # per-link overrides

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['user', 'algo', 'account'], name='uniq_link_per_user_algo_account'),
            # One default per (user, algo)
            UniqueConstraint(
                fields=['user', 'algo'],
                condition=Q(is_default=True),
                name='uniq_default_account_per_user_algo'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'algo']),
        ]

    def __str__(self):
        return f"{self.user.username} · Algo#{self.algo_id} → {self.account.label} ({self.role})"


class GlobalVariable(models.Model):
    """
    Shared knobs consumed by variable functions via env["globals"].
    Scope: global (no algo/user), per-algo, or per-user.
    """
    DTYPE = (('text', 'Text'), ('number', 'Number'), ('json', 'JSON'))
    key = models.CharField(max_length=100)
    value = models.JSONField(blank=True, null=True)
    dtype = models.CharField(max_length=20, choices=DTYPE, default='text')

    algo = models.ForeignKey('AlgorithmLogic', null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['key', 'algo', 'user'], name='uniq_global_key_scope')
        ]

    def __str__(self):
        scope = "GLOBAL" if not (self.algo_id or self.user_id) else f"a={self.algo_id or '-'} u={self.user_id or '-'}"
        return f"{self.key} [{scope}]"



class AlgoList(models.Model):
    algo_name = models.CharField(max_length=100, unique=True)
    minimum_fund_reqd = models.IntegerField()
    algo_description = models.TextField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='algos_created'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.algo_name

class AlgorithmLogic(models.Model):
    algo = models.ForeignKey(AlgoList, on_delete=models.CASCADE, related_name="legs")
    num_stocks = models.IntegerField()
    instrument_name = models.CharField(max_length=100)
    exchange_segment = models.CharField(max_length=16, default='NFO')  # pick your default
    expiry_date = models.CharField(max_length=20)
    strike_price = models.CharField(max_length=20)
    # models.py → class AlgorithmLogic
    # position sizing
    lot_qty = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    lot_size_snapshot = models.PositiveIntegerField(null=True, blank=True)  # filled from InstrumentList on save
    # strike selection mode
    STRIKE_KIND = (('ABS','Absolute'), ('ATM','ATM'), ('OTM','OTM'))
    strike_kind = models.CharField(max_length=8, choices=STRIKE_KIND, default='ABS')
    strike_target = models.CharField(max_length=64, blank=True, default='')  # numeric points or UDV name

    option_type = models.CharField(max_length=10)

    # 🆕 Added fields for order direction and order type
    order_direction = models.CharField(
        max_length=10,
        choices=[('Buy', 'Buy'), ('Sell', 'Sell')]
    )
    order_type = models.CharField(
        max_length=20,
        choices=[
            ('Market', 'Market'),
            ('Limit', 'Limit'),
            ('LimitThenMarket', 'LimitThenMarket')
        ]
    )

    def __str__(self):
        return f"Leg {self.num_stocks} - {self.instrument_name} - {self.option_type} - {self.order_direction}/{self.order_type}"

# models.py
class LegExecutionSnapshot(models.Model):
    """
    What we finally traded for a leg (resolved at order time).
    One row per (run, leg index, attempt), so you can track re-entries.
    """
    run = models.ForeignKey('AlgoRun', on_delete=models.CASCADE, related_name='leg_snapshots')  # you already have AlgoRun
    leg = models.ForeignKey('AlgorithmLogic', on_delete=models.CASCADE, related_name='snapshots')
    attempt = models.PositiveIntegerField(default=1)

    resolved_symbol = models.CharField(max_length=100)     # e.g. NFO:BANKNIFTY24AUG46000CE
    resolved_token  = models.CharField(max_length=32, blank=True)  # optional, broker/instrument token
    resolved_expiry = models.CharField(max_length=20, blank=True)
    resolved_strike = models.CharField(max_length=20, blank=True)

    lot_qty   = models.PositiveIntegerField(default=1)
    lot_size  = models.PositiveIntegerField(default=0)
    option_type = models.CharField(max_length=10, blank=True)   # CE/PE
    order_type  = models.CharField(max_length=20, blank=True)   # Market/Limit...
    order_direction = models.CharField(max_length=10, blank=True)  # Buy/Sell

    filled_qty = models.IntegerField(default=0)  # contracts filled (optional)
    meta = models.JSONField(default=dict, blank=True)  # any extra resolver info (ATM LTP, strike list, UDV value, etc.)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['run','leg','attempt'])]

class AlgoRegister(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    algo = models.ForeignKey(AlgorithmLogic, on_delete=models.CASCADE)
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE)
    broker_username = models.TextField()
    api_key = models.CharField(max_length=1000, blank=True, null=True)
    secret_key = models.CharField(max_length=1000, blank=True, null=True)

    def __str__(self):
        return f"{self.algo.algo.algo_name} by {self.user.username}"

class AlgoStatus(models.Model):
    algo_register = models.OneToOneField(AlgoRegister, on_delete=models.CASCADE)
    lot_size = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=50)
    profit_percentage = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    number_of_subscribers = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.status


class AlgoVariable(models.Model):
    algo = models.ForeignKey(AlgoList, on_delete=models.CASCADE, related_name='variables')
    name = models.CharField(max_length=100, unique=True)
    expression = models.TextField()  # Example: 'supertrend_5min * 6'

class Condition(models.Model):
    algo_logic = models.ForeignKey(AlgorithmLogic, on_delete=models.CASCADE, related_name='conditions')
    condition_type = models.CharField(max_length=10, choices=[('entry', 'Entry'), ('exit', 'Exit')])

    lhs_variable = models.CharField(max_length=100)  # e.g., "supertrend"
    lhs_parameters = models.JSONField(default=dict, blank=True)  # e.g., {"symbol": "NIFTY", "period": 10}

    operator = models.CharField(max_length=10, choices=[
        ('>', '>'), ('<', '<'), ('>=', '>='), ('<=', '<='), ('==', '=='), ('!=', '!=')
    ])

    rhs_type = models.CharField(max_length=50, choices=[('value', 'Value'), ('variable', 'Variable')])
    rhs_value = models.CharField(max_length=100, blank=True, null=True)  # Used if rhs_type == value
    rhs_variable = models.CharField(max_length=100, blank=True, null=True)  # Used if rhs_type == variable
    rhs_parameters = models.JSONField(default=dict, blank=True)  # Used if rhs_type == variable

    connector = models.CharField(max_length=3, choices=[('AND', 'AND'), ('OR', 'OR')])
    nested_condition = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')

    def __str__(self):
        return f"{self.lhs_variable} {self.operator} {self.rhs_value or self.rhs_variable}"

class InstrumentList(models.Model):
    token = models.CharField(max_length=50)
    symbol = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    expiry = models.CharField(max_length=50, blank=True, null=True)
    strike = models.FloatField(blank=True, null=True)
    lotsize = models.IntegerField(blank=True, null=True)
    instrumenttype = models.CharField(max_length=50, blank=True, null=True)
    exch_seg = models.CharField(max_length=50, blank=True, null=True)
    tick_size = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.symbol

class StatusColorMap(models.Model):
    status = models.TextField()
    color = models.TextField()

    def __str__(self):
        return self.status

# core/models.py
class VariableCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class VariableParameter(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g. symbol, lag, constant, multiplier
    description = models.TextField(blank=True)

    input_type = models.CharField(
        max_length=50,
        choices=[('text', 'Text'), ('number', 'Number'), ('select', 'Select')],
        default='text'
    )

    source_model = models.CharField(max_length=100, blank=True, null=True)   # optional
    source_field = models.CharField(max_length=100, blank=True, null=True)   # optional
    allowed_values = models.TextField(blank=True, null=True)
    default_value = models.CharField(max_length=100, blank=True, null=True)  # e.g., "3", "0.5"

    def __str__(self):
        return self.name

class Variable(models.Model):
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    category = models.ForeignKey(VariableCategory, on_delete=models.CASCADE)
    parameter_required = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    parameters = models.ManyToManyField(VariableParameter, blank=True)
    function_code = models.TextField(blank=True, null=True)  # <-- Add this line!

    def __str__(self):
        return self.display_name


class TechnicalIndicator(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g., "Supertrend"
    display_name = models.CharField(max_length=100)       # e.g., "Supertrend (5min)"
    function_code = models.TextField(blank=True, null=True)  # e.g., the actual logic or reference string
    default_params = models.JSONField(blank=True, null=True) # e.g., {"period": 10, "multiplier": 3}
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.display_name


class UserDefinedVariable(models.Model):
    algo = models.ForeignKey(AlgoList, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # ✅ add this line
    name = models.CharField(max_length=100)
    expression = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('algo', 'user', 'name')  # ✅ enforce uniqueness per user per algo

# models.py
class PlatformSetting(models.Model):
    key   = models.CharField(max_length=64, unique=True)
    value = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class AlgoOffer(models.Model):
    """
    A 'listing' for an AlgoList the creator wants to share/sell.
    One AlgoList can have 0..N offers (e.g., private invite-only, public, enterprise).
    """
    VISIBILITY_CHOICES = [
        ("public", "Public"),       # discoverable by all
        ("unlisted", "Unlisted"),   # by link/invite only
        ("private", "Private"),     # requires explicit invite/sub
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("paused", "Paused"),
        ("archived", "Archived"),
    ]
    platform_fee_pct = models.PositiveIntegerField(default=15, help_text="Platform share % of net(after discounts)")
    # You can add creator_share_pct later if you want revenue splits beyond '100 - platform'
    algo_list     = models.ForeignKey('AlgoList', on_delete=models.CASCADE, related_name='offers')
    owner         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='offers_owned')
    title         = models.CharField(max_length=200)
    tagline       = models.CharField(max_length=280, blank=True)
    description   = models.TextField(blank=True)
    visibility    = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default="unlisted")
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    max_subs      = models.PositiveIntegerField(null=True, blank=True, help_text="Cap subscribers; blank = no cap")
    allow_trial   = models.BooleanField(default=True)
    default_trial_days = models.PositiveIntegerField(default=7)

    # optional marketing/meta
    tags          = models.JSONField(default=list, blank=True)   # ["banknifty", "intraday"]
    preview_stats = models.JSONField(default=dict, blank=True)   # last 30d pnl, sharpe, etc.
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['status', 'visibility'])]

    def __str__(self):
        return f"{self.title} (#{self.id})"


class AlgoPlan(models.Model):
    """
    Pricing & billing cadence for an offer.
    """
    PERIOD_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
    ]
    offer        = models.ForeignKey(AlgoOffer, on_delete=models.CASCADE, related_name='plans')
    name         = models.CharField(max_length=100, default="Standard")
    period       = models.CharField(max_length=10, choices=PERIOD_CHOICES, default="monthly")
    price_minor  = models.PositiveIntegerField(default=0)  # price in minor unit (e.g., INR paise)
    currency     = models.CharField(max_length=3, default="INR")  # "INR"
    trial_days   = models.PositiveIntegerField(null=True, blank=True)  # override offer default if set
    is_active    = models.BooleanField(default=True)
# models.py (add to AlgoPlan)
    provider          = models.CharField(max_length=20, blank=True)        # "razorpay" | "stripe"
    provider_plan_id  = models.CharField(max_length=80, blank=True)        # Razorpay plan id
    stripe_price_id   = models.CharField(max_length=80, blank=True)        # Stripe price id
    
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('offer', 'name', 'period')


class AlgoInvitation(models.Model):
    """
    Token-based invites to subscribe to an offer (optionally a specific plan).
    Can carry a discount (% or amount) or free-trial override.
    """
    DISCOUNT_TYPE = [
        ("percent", "Percent"),
        ("amount", "Amount"),
        ("none", "None"),
    ]

    offer        = models.ForeignKey(AlgoOffer, on_delete=models.CASCADE, related_name='invites')
    plan         = models.ForeignKey(AlgoPlan, null=True, blank=True, on_delete=models.SET_NULL)
    inviter      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invites_sent')
    invitee      = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='invites_received')
    invitee_email= models.EmailField(blank=True)
    token        = models.CharField(max_length=64, unique=True, default=invite_token,editable=False)
    message      = models.CharField(max_length=280, blank=True)

    discount_type= models.CharField(max_length=10, choices=DISCOUNT_TYPE, default="none")
    discount_val = models.PositiveIntegerField(default=0, help_text="percent (0-100) or minor amount")
    trial_days   = models.PositiveIntegerField(null=True, blank=True)

    expires_at   = models.DateTimeField(null=True, blank=True)
    redeemed_at  = models.DateTimeField(null=True, blank=True)
    is_revoked   = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['token'])]


class AlgoSubscription(models.Model):
    """
    The commercial subscription record (who, what offer/plan, and billing state).
    When active/trialing, it grants entitlement to the underlying AlgoList.
    """
    STATUS = [
        ("trialing", "Trialing"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("canceled", "Canceled"),
        ("expired", "Expired"),
    ]

    subscriber   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='algo_subscriptions')
    offer        = models.ForeignKey(AlgoOffer, on_delete=models.CASCADE, related_name='subscriptions')
    plan         = models.ForeignKey(AlgoPlan, on_delete=models.PROTECT, related_name='subscriptions')

    status       = models.CharField(max_length=10, choices=STATUS, default="trialing")
    started_at   = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    # Optional payment system linkage (fill via checkout/webhooks)
    payment_provider    = models.CharField(max_length=20, blank=True)     # "razorpay" / "stripe"
    provider_cust_id    = models.CharField(max_length=64, blank=True)
    provider_sub_id     = models.CharField(max_length=64, blank=True)
    last_payment_at     = models.DateTimeField(null=True, blank=True)

    # Audit / source
    invitation     = models.ForeignKey(AlgoInvitation, null=True, blank=True, on_delete=models.SET_NULL)
    promo_code     = models.CharField(max_length=50, blank=True)

    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('subscriber', 'offer')


class AlgoEntitlement(models.Model):
    """
    Fast access-check table (denormalized). Row exists IFF user can see/run the algo.
    Recomputed on sub/offer status changes (signal).
    """
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    algo_list   = models.ForeignKey('AlgoList', on_delete=models.CASCADE)
    source      = models.CharField(max_length=20, default="subscription")   # "owner" | "admin" | "subscription" | "invite_free"
    valid_from  = models.DateTimeField(default=timezone.now)
    valid_to    = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'algo_list')


class HiddenAlgo(models.Model):
    """
    (From earlier) purely a UI preference.
    """
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    algo       = models.ForeignKey('AlgoList', on_delete=models.CASCADE)
    hidden_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user','algo')


# -------- Optional but useful for payouts & invoices (add later if needed) -----

class PayoutAccount(models.Model):
    """
    Where the creator wants funds (supports India): UPI ID, bank details, PAN/GST.
    """
    user        = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payout_account')
    upi_id      = models.CharField(max_length=100, blank=True)
    bank_ifsc   = models.CharField(max_length=20, blank=True)
    bank_ac_no  = models.CharField(max_length=50, blank=True)
    pan         = models.CharField(max_length=15, blank=True)
    gstin       = models.CharField(max_length=20, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)





class Invoice(models.Model):
    # who/what
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoices')
    offer        = models.ForeignKey(AlgoOffer, on_delete=models.SET_NULL, null=True)
    subscription = models.ForeignKey('AlgoSubscription', null=True, blank=True, on_delete=models.SET_NULL)
    currency     = models.CharField(max_length=3, default="INR")
    # pricing breakdown
    gross_minor      = models.PositiveIntegerField()                # list price for the period
    discount_minor   = models.PositiveIntegerField(default=0)       # coupon/invite discount
    net_minor        = models.PositiveIntegerField()                # gross - discount
    platform_fee_pct = models.PositiveIntegerField(default=15)      # snapshot
    platform_fee_minor = models.PositiveIntegerField(default=0)     # computed on net
    creator_gross_minor = models.PositiveIntegerField(default=0)    # net - platform_fee
    gst_pct          = models.PositiveIntegerField(default=18)      # snapshot (if you collect GST)
    gst_minor        = models.PositiveIntegerField(default=0)       # GST on platform fee (if platform is the merchant)
    tds_pct          = models.PositiveIntegerField(default=0)       # snapshot
    tds_minor        = models.PositiveIntegerField(default=0)       # if applicable (B2B)
    creator_payout_minor = models.PositiveIntegerField(default=0)   # creator_gross - tds (and minus any creator GST collected by themselves if applicable)
    status       = models.CharField(max_length=12, default="paid")  # paid/void/refund
    issued_at    = models.DateTimeField(default=timezone.now)

class CreatorEarning(models.Model):
    creator     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='creator_earnings')
    invoice     = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='earning')
    offer       = models.ForeignKey(AlgoOffer, on_delete=models.SET_NULL, null=True)
    amount_minor= models.PositiveIntegerField()     # creator_payout_minor
    created_at  = models.DateTimeField(auto_now_add=True)
    settled     = models.BooleanField(default=False)
    settled_at  = models.DateTimeField(null=True, blank=True)
    batch_id    = models.CharField(max_length=64, blank=True)  # tie to a payout batch

class PayoutBatch(models.Model):
    """
    When you actually transfer money (UPI/Bank), close a batch for audit.
    """
    created_at  = models.DateTimeField(auto_now_add=True)
    note        = models.CharField(max_length=200, blank=True)
    total_minor = models.PositiveIntegerField(default=0)

# models.py (add near your other marketplace models)


class WebhookEvent(models.Model):
    """
    Idempotency & audit for incoming payment webhooks.
    One row per provider event. Keep raw payload (minus secrets) for debugging.
    """
    provider    = models.CharField(max_length=20)              # "razorpay" | "stripe" | ...
    event_id    = models.CharField(max_length=120, unique=True)
    received_at = models.DateTimeField(auto_now_add=True)
    raw         = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['provider', 'received_at']),
        ]

    def __str__(self):
        return f"{self.provider}:{self.event_id}"







