from django.contrib import admin
from .models import (
    User, Broker, AlgoList, AlgoRegister, AlgoStatus,
    InstrumentList, StatusColorMap,Condition, AlgorithmLogic,Condition,AlgoStatusStyle
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
@admin.register(AlgoStatusStyle)
class AlgoStatusStyleAdmin(admin.ModelAdmin):
    list_display = ('key','label','user','bulma_tag_class','bulma_bg_class','dot_hex','enabled','order')
    list_filter  = ('user','key','enabled')
    search_fields = ('label',)