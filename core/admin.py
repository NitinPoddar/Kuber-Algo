from django.contrib import admin
from .models import (
    User, Broker, AlgoList, AlgoRegister, AlgoStatus,
    InstrumentList, StatusColorMap,Condition, AlgorithmLogic,Condition
)

admin.site.register(User)
admin.site.register(Broker)
admin.site.register(AlgoList)
admin.site.register(AlgoRegister)
admin.site.register(AlgoStatus)
admin.site.register(InstrumentList)
admin.site.register(StatusColorMap)
admin.site.register(Condition)
admin.site.register(AlgorithmLogic)
