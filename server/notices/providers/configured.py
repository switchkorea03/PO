"""SOLAPI adapter; live calls require explicit private configuration."""
import hashlib,hmac,json,secrets
from datetime import datetime,timedelta,timezone
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError,URLError
from django.conf import settings
from .base import SendResult,ProviderStatus,split_text

class ConfiguredSmsProvider:
    def __init__(self):
        if not settings.SMS_LIVE_ENABLED or not settings.SMS_API_KEY or not settings.SMS_API_SECRET:raise ValueError('문자 공급자 인증정보·실발송 설정이 미완료입니다.')
    def split(self,body):return split_text(body,1900)
    def _request(self,path,payload=None):
        now=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z');salt=secrets.token_hex(16)
        signature=hmac.new(settings.SMS_API_SECRET.encode(),(now+salt).encode(),hashlib.sha256).hexdigest()
        auth=f'HMAC-SHA256 apiKey={settings.SMS_API_KEY}, date={now}, salt={salt}, signature={signature}'
        req=Request('https://api.solapi.com'+path,data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,headers={'Authorization':auth,'Content-Type':'application/json'})
        with urlopen(req,timeout=20) as response:return json.load(response)
    def send(self,request):
        payload={'messages':[{'to':request.recipient,'from':request.sender,'text':request.body,'autoTypeDetect':True,'customFields':{'clientKey':request.client_key}}],'showMessageList':True,'allowDuplicates':False}
        try:
            result=self._request('/messages/v4/send-many/detail',payload)
            entries=result.get('messageList',[])
            if isinstance(entries,dict):entries=list(entries.values())
            for entry in entries:
                if entry.get('statusCode')=='2000':return SendResult('accepted',entry.get('messageId'),'서비스 정상 접수')
            failed=result.get('failedMessageList',[])
            if failed:return SendResult('failed',failed[0].get('messageId'),'공급자 접수 거부: '+str(failed[0].get('statusCode','')))
            return SendResult('unknown',None,'개별 메시지 접수 결과 없음')
        except HTTPError as exc:return SendResult('failed' if 400<=exc.code<500 else 'unknown',None,f'공급자 HTTP {exc.code}')
        except (URLError,TimeoutError,ValueError,OSError):return SendResult('unknown',None,'공급자 응답 미확정')
    def lookup(self,client_key,provider_id):
        query={'limit':500}
        if provider_id:query.update({'criteria':'messageId','cond':'eq','value':provider_id})
        else:query['startDate']=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
        matches=[]
        try:
            for _ in range(5):
                result=self._request('/messages/v4/list?'+urlencode(query));messages=result.get('messageList',{})
                entries=list(messages.values()) if isinstance(messages,dict) else messages
                matches.extend(m for m in entries if (provider_id and m.get('messageId')==provider_id) or m.get('customFields',{}).get('clientKey')==client_key)
                if matches or not result.get('nextKey'):break
                query['startKey']=result['nextKey']
        except (HTTPError,URLError,TimeoutError,ValueError,OSError):return ProviderStatus('unknown',provider_id,'발송 내역 조회 미확정')
        if not matches:return ProviderStatus('unknown',provider_id,'공급자 내역에서 접수 결과를 확인하세요.')
        entry=next((m for m in matches if m.get('statusCode')=='4000'),matches[0]);code=str(entry.get('statusCode',''))
        if code=='4000':status='delivered'
        elif entry.get('status') in ('PENDING','SENDING') or code=='2000':status='accepted'
        elif entry.get('status')=='COMPLETE' and code:status='failed'
        else:status='unknown'
        return ProviderStatus(status,entry.get('messageId') or provider_id,'공급자 상태: '+code)
