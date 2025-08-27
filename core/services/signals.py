# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 00:43:18 2025

@author: Home
"""

# signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.models import AlgoOffer, AlgoSubscription, AlgoEntitlement

def _rebuild_entitlements_for_offer(offer):
    # Owner always entitled
    AlgoEntitlement.objects.get_or_create(user=offer.owner, algo_list=offer.algo_list, defaults={"source":"owner"})
    # Admin/staff can be handled globally or here if you want blanket access.

    # Subscriptions -> active/trialing only
    active = offer.subscriptions.filter(status__in=["active","trialing"])
    have = set(AlgoEntitlement.objects.filter(algo_list=offer.algo_list, source="subscription")
               .values_list("user_id", flat=True))
    want = set(active.values_list("subscriber_id", flat=True))

    # add missing
    for uid in (want - have):
        AlgoEntitlement.objects.get_or_create(user_id=uid, algo_list=offer.algo_list, defaults={"source":"subscription"})
    # remove extras
    for uid in (have - want):
        AlgoEntitlement.objects.filter(user_id=uid, algo_list=offer.algo_list, source="subscription").delete()

@receiver(post_save, sender=AlgoOffer)
def _offer_changed(sender, instance, **kwargs):
    _rebuild_entitlements_for_offer(instance)

@receiver(post_save, sender=AlgoSubscription)
def _sub_changed(sender, instance, **kwargs):
    _rebuild_entitlements_for_offer(instance.offer)

@receiver(post_delete, sender=AlgoSubscription)
def _sub_deleted(sender, instance, **kwargs):
    _rebuild_entitlements_for_offer(instance.offer)
