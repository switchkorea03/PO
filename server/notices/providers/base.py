from dataclasses import dataclass
from typing import Protocol
@dataclass(frozen=True)
class SendRequest:
    client_key:str
    recipient:str
    sender:str
    body:str
@dataclass(frozen=True)
class SendResult:
    status:str
    provider_id:str|None=None
    reason:str|None=None
@dataclass(frozen=True)
class ProviderStatus:
    status:str
    provider_id:str|None=None
    reason:str|None=None
class SmsProvider(Protocol):
    def send(self,request:SendRequest)->SendResult:...
    def lookup(self,client_key:str,provider_id:str|None)->ProviderStatus:...
    def split(self,body:str)->tuple[str,...]:...

def split_text(body,byte_limit=1900):
    chunks=[];current='';length=0
    for char in body:
        size=len(char.encode('utf-8'))
        if length+size>byte_limit:chunks.append(current);current='';length=0
        current+=char;length+=size
    if current:chunks.append(current)
    return tuple(chunks)
