from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class User(AbstractUser):
    name = models.CharField(max_length=1000)

class Broker(models.Model):
    broker_name = models.CharField(max_length=100, unique=True)
    root_api = models.TextField()
    server_ip = models.TextField(blank=True, null=True)
    authenticator_req = models.IntegerField(blank=True, null=True)
    password_req = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.broker_name

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

    default_value = models.CharField(max_length=100, blank=True, null=True)  # e.g., "3", "0.5"

    def __str__(self):
        return self.name

class Variable(models.Model):
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    category = models.ForeignKey(VariableCategory, on_delete=models.CASCADE)
    parameter_required = models.BooleanField(default=False)

    parameters = models.ManyToManyField(VariableParameter, blank=True)

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

