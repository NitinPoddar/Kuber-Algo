from django.contrib import admin
from core.models import (
    User, Broker, AlgoList, AlgoRegister, AlgoStatus,
    InstrumentList, StatusColorMap,AlgorithmLogic,Condition,AlgoStatusStyle
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

# admin.py
from django.contrib import admin
from .models import Invoice, CreatorEarning, WebhookEvent, AlgoOffer, AlgoPlan, AlgoSubscription

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display  = ("id", "user", "offer", "currency", "gross_minor", "discount_minor",
                     "net_minor", "platform_fee_minor", "creator_payout_minor",
                     "status", "issued_at")
    list_filter   = ("status", "currency", "issued_at", "offer")
    search_fields = ("id", "user__username", "user__email", "offer__title")
    date_hierarchy = "issued_at"

@admin.register(CreatorEarning)
class CreatorEarningAdmin(admin.ModelAdmin):
    list_display  = ("id", "creator", "offer", "amount_minor", "settled", "created_at", "settled_at")
    list_filter   = ("settled", "created_at")
    search_fields = ("id", "creator__username", "creator__email", "offer__title")
    date_hierarchy = "created_at"

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display  = ("event_id", "provider", "received_at")
    list_filter   = ("provider", "received_at")
    search_fields = ("event_id",)
    date_hierarchy = "received_at"

# Optional: quick admin for marketplace objects
@admin.register(AlgoOffer)
class AlgoOfferAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "status", "visibility", "platform_fee_pct", "created_at")
    list_filter  = ("status", "visibility", "created_at")
    search_fields = ("title", "owner__username", "owner__email")

@admin.register(AlgoPlan)
class AlgoPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "offer", "name", "period", "price_minor", "currency", "is_active")
    list_filter  = ("period", "is_active", "currency")
    search_fields = ("offer__title", "name")

@admin.register(AlgoSubscription)
class AlgoSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "subscriber", "offer", "plan", "status", "payment_provider",
                    "provider_sub_id", "current_period_end", "last_payment_at")
    list_filter  = ("status", "payment_provider")
    search_fields = ("subscriber__username", "subscriber__email", "offer__title", "provider_sub_id")
