from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db.models import Q, UniqueConstraint


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
    expiry_date = models.CharField(max_length=20)
    strike_price = models.CharField(max_length=20)
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

    rhs_type = models.CharField(max_length=10, choices=[('value', 'Value'), ('variable', 'Variable')])
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

