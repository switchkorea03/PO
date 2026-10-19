from collections import Counter
from .base import SendResult,ProviderStatus,split_text
class SimulatedCrash(BaseException):pass
class FakeSmsProvider:
    def __init__(self,outcome='delivered',crash_after_accept=False,byte_limit=1900):
        self.outcome=outcome;self.crash_after_accept=crash_after_accept;self.byte_limit=byte_limit;self.receipts={};self.counts=Counter()
    def split(self,body):return split_text(body,self.byte_limit)
    def send(self,request):
        if request.client_key in self.receipts and self.receipts[request.client_key].status in ('accepted','delivered'):return self.receipts[request.client_key]
        result=SendResult(self.outcome,'fake-'+request.client_key,'모의 발송')
        if self.outcome in ('accepted','delivered'):self.counts[request.client_key]+=1
        self.receipts[request.client_key]=result
        if self.crash_after_accept:
            self.crash_after_accept=False;raise SimulatedCrash()
        return result
    def lookup(self,client_key,provider_id):
        result=self.receipts.get(client_key)
        return ProviderStatus(result.status,result.provider_id,result.reason) if result else ProviderStatus('unknown',provider_id,'조회 결과 미확정')
    def accepted_count(self,client_key):return self.counts[client_key]
