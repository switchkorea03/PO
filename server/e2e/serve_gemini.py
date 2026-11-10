"""Isolated UI/DB integration harness; Gemini is always a local stub here."""
import os,sys,runpy
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
os.environ['DJANGO_SETTINGS_MODULE']='config.e2e_settings'
import django
django.setup()
from django.conf import settings
from intake.tests.test_gemini import AI_DOCUMENT
from intake.gemini import normalize_proposal
import intake.ai_services
settings.GEMINI_API_KEY='e2e-stub-never-a-real-key'
def stub(source,local_result):
    return {'result':normalize_proposal(AI_DOCUMENT,local_result),'usage':{'input':20,'output':30,'total':50}}
intake.ai_services.analyze_source=stub
runpy.run_path(str(root/'e2e'/'serve.py'),run_name='__main__')
