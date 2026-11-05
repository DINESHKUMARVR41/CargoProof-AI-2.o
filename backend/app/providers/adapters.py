"""Configurable provider adapters. No undocumented vendor endpoints are assumed."""
import asyncio
from datetime import datetime,timezone
import httpx
from .base import BaseProvider
from ..config import settings

class ConfiguredHttpProvider(BaseProvider):
    def __init__(self,name,capabilities,base_url,endpoint,api_key):
        self.name=name; self.capabilities=capabilities; self.base_url=base_url.rstrip('/'); self.endpoint=endpoint.strip(); self.api_key=api_key
        super().__init__(enabled=bool(settings.live_provider_mode and self.base_url and self.endpoint and self.api_key))
    async def fetch_with_x402(self,resource_id,capability,idempotency_key=None):
        if not self.enabled:return self.unavailable('Live provider is not configured')
        url=self.base_url+'/'+self.endpoint.lstrip('/')
        headers={'Accept':'application/json','Authorization':f'Bearer {self.api_key}'}
        if idempotency_key:headers['Idempotency-Key']=idempotency_key
        from ..payments.x402 import paid_httpx_request
        response,settlement=await paid_httpx_request(url,{'resource_id':resource_id,'capability':capability},headers)
        try:data=response.json()
        except ValueError:return {'provider':self.name,'status':'INVALID_RESPONSE','source_type':'LIVE_OBSERVATION','retrieved_at':datetime.now(timezone.utc).isoformat(),'evidence':None,'settlement':settlement,'http_status':response.status_code,'error':'Payment confirmed but provider response was not valid JSON'}
        if not isinstance(data,dict):return {'provider':self.name,'status':'INVALID_RESPONSE','source_type':'LIVE_OBSERVATION','retrieved_at':datetime.now(timezone.utc).isoformat(),'evidence':None,'settlement':settlement,'http_status':response.status_code,'error':'Payment confirmed but provider response was not a JSON object'}
        return {'provider':self.name,'status':'AVAILABLE','source_type':'LIVE_OBSERVATION','observed_at':data.get('observed_at') or data.get('timestamp'),'retrieved_at':datetime.now(timezone.utc).isoformat(),'evidence':data,'settlement':settlement,'http_status':response.status_code}

    async def fetch(self,resource_id,**kwargs):
        if not self.enabled:return self.unavailable('Live provider disabled or base URL, documented endpoint, or API key missing')
        url=self.base_url+'/'+self.endpoint.lstrip('/')
        headers={'Accept':'application/json','Authorization':f'Bearer {self.api_key}'}
        idem=kwargs.pop('_idempotency_key',None)
        if idem:headers['Idempotency-Key']=idem
        last=None
        for attempt in range(settings.provider_max_retries+1):
            try:
                async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds,follow_redirects=False) as client:
                    response=await client.get(url,params={'resource_id':resource_id,**kwargs},headers=headers)
                if response.status_code==402:
                    requirement=response.headers.get('PAYMENT-REQUIRED')
                    if not requirement:return {'provider':self.name,'status':'PAYMENT_REQUIRED_UNSUPPORTED','http_status':402,'retrieved_at':datetime.now(timezone.utc).isoformat(),'evidence':None,'error':'Provider did not return the x402 V2 PAYMENT-REQUIRED header'}
                    return {'provider':self.name,'status':'PAYMENT_REQUIRED','http_status':402,'payment_required':requirement,'retrieved_at':datetime.now(timezone.utc).isoformat(),'evidence':None}
                response.raise_for_status(); data=response.json()
                if not isinstance(data,dict):return self.unavailable('Provider response must be a JSON object','INVALID_RESPONSE')
                return {'provider':self.name,'status':'AVAILABLE','source_type':'LIVE_OBSERVATION','observed_at':data.get('observed_at') or data.get('timestamp'),'retrieved_at':datetime.now(timezone.utc).isoformat(),'evidence':data,'http_status':response.status_code}
            except (httpx.TimeoutException,httpx.HTTPError,ValueError) as exc:
                last=f'{type(exc).__name__}: {exc}'
                if attempt<settings.provider_max_retries:await asyncio.sleep(.2*(attempt+1))
        return self.unavailable(last or 'Provider request failed')

class StraleProvider(ConfiguredHttpProvider):
    def __init__(self):super().__init__('strale',['container_tracking','container_validation','container_vessel_association'],settings.strale_api_base,settings.strale_endpoint,settings.strale_api_key)
class AisfleetProvider(ConfiguredHttpProvider):
    def __init__(self):super().__init__('aisfleet',['vessel_position','vessel_identity','port_calls','vessel_status'],settings.aisfleet_api_base,settings.aisfleet_endpoint,settings.aisfleet_api_key)
class SynthoraProvider(ConfiguredHttpProvider):
    def __init__(self):super().__init__('synthora',['port_activity','port_anomalies','inspection','shipping_documents'],settings.synthora_api_base,settings.synthora_endpoint,settings.synthora_api_key)

class SandboxX402Provider(BaseProvider):
    """Explicitly synthetic paid provider used to exercise the GoPlausible x402 path on TestNet."""
    name='cargoproof_test_provider'
    capabilities=['container_tracking','container_validation','container_vessel_association','vessel_identity','vessel_position','vessel_status','port_calls','port_activity','port_anomalies','inspection','shipping_documents']
    source_type='SANDBOX_PROVIDER_DATA'
    def __init__(self):
        self.base_url=settings.test_provider_base_url.rstrip('/');self.endpoint='/api/test-provider/evidence'
        enabled=bool(settings.test_provider_enabled and not settings.demo_mode and settings.x402_enabled and settings.x402_avm_mnemonic and settings.test_provider_pay_to)
        super().__init__(enabled=enabled)
    async def fetch(self,resource_id,**kwargs):
        if not self.enabled:return self.unavailable('x402 sandbox provider is not enabled/configured')
        headers={'Accept':'application/json'};idem=kwargs.pop('_idempotency_key',None)
        if idem:headers['Idempotency-Key']=idem
        try:
            async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds,follow_redirects=False) as client:
                response=await client.get(self.base_url+self.endpoint,params={'resource_id':resource_id,**kwargs},headers=headers)
            if response.status_code==402:
                requirement=response.headers.get('PAYMENT-REQUIRED')
                if not requirement:return self.unavailable('Sandbox provider did not return x402 V2 PAYMENT-REQUIRED','PAYMENT_REQUIRED_UNSUPPORTED')
                return {'provider':self.name,'status':'PAYMENT_REQUIRED','http_status':402,'payment_required':requirement,'retrieved_at':datetime.now(timezone.utc).isoformat(),'evidence':None}
            response.raise_for_status();data=response.json()
            return {'provider':self.name,'status':'AVAILABLE','source_type':self.source_type,'observed_at':data.get('observed_at'),'retrieved_at':datetime.now(timezone.utc).isoformat(),'evidence':data,'http_status':response.status_code}
        except (httpx.TimeoutException,httpx.HTTPError,ValueError) as exc:return self.unavailable(f'{type(exc).__name__}: {exc}')
    async def fetch_with_x402(self,resource_id,capability,idempotency_key=None,**context):
        if not self.enabled:return self.unavailable('x402 sandbox provider is not enabled/configured')
        from ..payments.x402 import paid_httpx_request
        headers={'Accept':'application/json'}
        if idempotency_key:headers['Idempotency-Key']=idempotency_key
        response,settlement=await paid_httpx_request(self.base_url+self.endpoint,{'resource_id':resource_id,'capability':capability,**context},headers)
        try:data=response.json()
        except ValueError:return {'provider':self.name,'status':'INVALID_RESPONSE','source_type':self.source_type,'retrieved_at':datetime.now(timezone.utc).isoformat(),'evidence':None,'settlement':settlement,'http_status':response.status_code,'error':'Payment confirmed but sandbox response was not valid JSON'}
        if not isinstance(data,dict):return {'provider':self.name,'status':'INVALID_RESPONSE','source_type':self.source_type,'retrieved_at':datetime.now(timezone.utc).isoformat(),'evidence':None,'settlement':settlement,'http_status':response.status_code,'error':'Payment confirmed but sandbox response was not a JSON object'}
        return {'provider':self.name,'status':'AVAILABLE','source_type':self.source_type,'observed_at':data.get('observed_at'),'retrieved_at':datetime.now(timezone.utc).isoformat(),'evidence':data,'settlement':settlement,'http_status':response.status_code}
