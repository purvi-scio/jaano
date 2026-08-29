import json, os, uuid, time, logging, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai.provider import enabled as ai_enabled, analyse as ai_analyse, response_analyse as ai_response_analyse
from ai.retriever import retrieve

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data'; FRONTEND=ROOT/'frontend'
with open(DATA/'authorities.json') as f: AUTHORITIES=json.load(f)
with open(DATA/'documents.json') as f: DOCUMENTS=json.load(f)
with open(DATA/'responses.json') as f: RESPONSES=json.load(f)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s jaano request_id=%(request_id)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger=logging.getLogger('jaano')

class RequestContext(logging.LoggerAdapter):
    def process(self,msg,kwargs):
        return msg, kwargs

RTIS_FILE=DATA/'rtis.json'
if RTIS_FILE.exists():
    try:
        with open(RTIS_FILE) as f: RTIS=json.load(f)
    except Exception:
        RTIS=[]
else:
    RTIS=[]


def classify(text):
    t=text.lower()
    if any(x in t for x in ['road','highway','nhai','construction','bridge']):
        return {'topic':'Infrastructure project','authority':AUTHORITIES['highway'],'requirements':['sanctioned amount','actual expenditure','contractor/work order','original and revised completion records'],'scenario':'highway'}
    if any(x in t for x in ['passport','passport office','rpo','passport application']):
        return {'topic':'Passport / consular service','authority':AUTHORITIES['passport'],'requirements':['application processing status','file movement/progress records','officer/office handling the file','recorded reason for delay, if documented'],'scenario':'passport'}
    return {'topic':'Government service / project','authority':AUTHORITIES['general'],'requirements':['relevant file/record showing current status','sanction/order or governing record','records showing action taken to date'],'scenario':'general'}


def public_info(scenario): return [d for d in DOCUMENTS if d['scenario']==scenario]


def build_request(missing):
    mapping={
      'actual expenditure':'Copy/details of expenditure incurred on the project to date, as available on record.',
      'contractor/work order':'Copy of the work order/contract and the name of the contractor or executing agency, as available on record.',
      'original and revised completion records':'Copy of the original completion schedule and any revised completion/extension order available on record.',
      'sanctioned amount':'Copy/details of the administrative sanction and sanctioned project amount, as available on record.',
      'application processing status':'The recorded status of the application and its current stage of processing, as available on record.',
      'file movement/progress records':'File movement/progress records showing action taken on the application, as available on record.',
      'officer/office handling the file':'Name/designation of the office or officer recorded as handling the application.',
      'recorded reason for delay, if documented':'Copies of records/orders noting any recorded reason for delay, if such records exist.',
      'relevant file/record showing current status':'Records showing the current status of the matter, as available on record.',
      'sanction/order or governing record':'Copy of the relevant sanction/order/official record.',
      'records showing action taken to date':'Records showing action taken by the public authority to date.'}
    return [mapping.get(x,x) for x in missing]


def mappings_for(scenario, missing):
    if scenario=='highway':
        base={'actual expenditure':('"Where did the money go?"','Project expenditure records','The amount actually spent is the evidence needed to answer the question.'),'original and revised completion records':('"Why is it delayed?"','Original + revised completion records','A recorded extension or revised schedule can establish what changed without asking the officer for an opinion.')}
    elif scenario=='passport':
        base={'application processing status':('"What stage is my passport at?"','Recorded application status','We ask for the status on file rather than asking the officer to explain it.'),'file movement/progress records':('"What happened to my application?"','File movement/progress records','The movement of the file provides a record of action taken.'),'officer/office handling the file':('"Who is handling it?"','Recorded officer/office details','We request the officer/office recorded on the file.'),'recorded reason for delay, if documented':('"Why is it delayed?"','Recorded reason/order, if documented','We ask for an existing record of the reason, not an opinion.')}
    else: base={}
    return [{'from':base[x][0],'to':base[x][1],'why':base[x][2]} for x in missing if x in base]


def save_rti(record):
    RTIS.append(record)
    with open(RTIS_FILE,'w') as f: json.dump(RTIS,f,indent=2)

def public_rti(record):
    return {k:v for k,v in record.items() if k not in {'name','email','address','citizen','bpl','bpl_certificate'}}

class Handler(BaseHTTPRequestHandler):
    def send_json(self,obj,status=200):
        raw=json.dumps(obj).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/api/health': return self.send_json({'ok':True})
        if self.path=='/' or self.path.startswith('/index.html'):
            raw=(FRONTEND/'index.html').read_bytes(); self.send_response(200); self.send_header('Content-Type','text/html'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if self.path.startswith('/static/'):
            # Strip query parameters (e.g. ?v=11.2) before resolving the static filename.
            # This keeps cache-busting URLs compatible with the simple local server.
            static_name=self.path.split('?',1)[0].replace('/static/','',1)
            p=FRONTEND/static_name
            if p.exists():
                raw=p.read_bytes(); ct='text/css' if p.suffix=='.css' else 'application/javascript'; self.send_response(200); self.send_header('Content-Type',ct); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        return self.send_json({'error':'not found'},404)
    def do_POST(self):
        n=int(self.headers.get('Content-Length','0')); body=json.loads(self.rfile.read(n) or '{}')
        if self.path=='/api/log':
            # UI telemetry is intentionally limited to non-sensitive interaction metadata.
            print(f"[Jaano] UI click: id={body.get('id','(no-id)')!r}, text={body.get('text','')!r}, screen={body.get('screen','(none)')!r}", flush=True)
            return self.send_json({'ok':True})
        if self.path=='/api/analyse':
            text=body.get('text','').strip()
            if not text: return self.send_json({'error':'Question is required'},400)
            # Real local retrieval happens before the model call. The corpus is synthetic for the hackathon,
            # but retrieval, ranking and evidence IDs are real.
            intent=classify(text)
            retrieved=retrieve(text, intent['scenario'], top_k=6)
            docs=public_info(intent['scenario'])
            evidence=[{k:v for k,v in d.items() if k in {'id','title','department','date','page','source_type','text','retrieval_score','matched_terms'}} for d in retrieved]
            print(f"[Jaano RAG] query={text[:80]!r} scenario={intent['scenario']} hits={len(evidence)} ids={[e['id'] for e in evidence]}", flush=True)
            ai_meta={'mode':'fallback','model':None}
            if ai_enabled():
                try:
                    directory={'highway':AUTHORITIES['highway'],'passport':AUTHORITIES['passport'],'general':AUTHORITIES['general']}
                    result, meta=ai_analyse(text,directory,evidence)
                    authority=directory.get(result['authority_key'],AUTHORITIES['general']).copy()
                    authority['confidence']=result['confidence']; authority['reason']=result['reason']
                    intent={'topic':result['topic'],'authority':authority,'requirements':result['requirements'],'scenario':result['scenario']}
                    missing=result['missing_requirements']
                    request_items=result['request_items']
                    mappings=result['mappings']
                    ai_meta={'mode':'live','model':meta['model'],'request_id':meta['request_id']}
                    print(f"[Jaano AI] live analysis model={meta['model']} request_id={meta['request_id']}",flush=True)
                except Exception as e:
                    print(f"[Jaano AI] live analysis failed; using fallback: {e}",flush=True)
                    missing=(['actual expenditure','original and revised completion records'] if intent['scenario']=='highway' else ['application processing status','file movement/progress records','recorded reason for delay, if documented'] if intent['scenario']=='passport' else intent['requirements'][:2])
                    request_items=build_request(missing); mappings=mappings_for(intent['scenario'],missing)
            else:
                missing=(['actual expenditure','original and revised completion records'] if intent['scenario']=='highway' else ['application processing status','file movement/progress records','recorded reason for delay, if documented'] if intent['scenario']=='passport' else intent['requirements'][:2])
                request_items=build_request(missing); mappings=mappings_for(intent['scenario'],missing)
            found=[fact for d in docs for fact in d.get('facts',[])]
            return self.send_json({'intent':intent,'documents':docs,'evidence':evidence,'found':found,'missing':missing,'request_items':request_items,'mappings':mappings,'ai':ai_meta,'retrieval':{'query':text,'count':len(evidence)},'prototype_notice':'Government records, authority data and submission are simulated for this prototype.'})
        if self.path=='/api/submit':
            print(f"[Jaano] /api/submit received: name={bool(body.get('name'))}, email_present={bool(body.get('email'))}, citizen={body.get('citizen', False)}, bpl={body.get('bpl',False)}, items={len(body.get('request_items') or [])}", flush=True)
            rid='RTI/2026/'+str(uuid.uuid4().int)[:6]
            authority=body.get('authority') or {}
            record={'registration_id':rid,'subject':body.get('question','Information request'),'authority':authority,'request_items':body.get('request_items') or [],'name':body.get('name',''),'email':body.get('email','').strip().lower(),'address':body.get('address',''),'citizen':bool(body.get('citizen')),'bpl':bool(body.get('bpl')),'bpl_certificate':body.get('bpl_certificate'),'status':'Submitted','filed_date':'29 Aug 2026','last_update':'Request received. It is being routed to the responsible desk.','timeline':[{'label':'Submitted','done':True,'description':'Request received'},{'label':'Being routed','done':False,'description':'Sent to responsible desk'},{'label':'Under review','done':False,'description':'CPIO reviews request'},{'label':'Response','done':False,'description':'Information arrives'}]}
            save_rti(record)
            print(f"[Jaano] RTI submitted successfully: {rid}", flush=True)
            return self.send_json(public_rti(record) | {'email':record['email']})
        if self.path=='/api/rtis/list':
            email=body.get('email','').strip().lower()
            matches=[public_rti(r) for r in RTIS if r.get('email','').lower()==email]
            print(f"[Jaano] /api/rtis/list email_present={bool(email)} matches={len(matches)}", flush=True)
            return self.send_json({'rtis':matches})
        if self.path=='/api/rtis/track':
            rid=body.get('registration_id','').strip(); email=body.get('email','').strip().lower()
            match=next((r for r in RTIS if r.get('registration_id')==rid and r.get('email','').lower()==email),None)
            print(f"[Jaano] /api/rtis/track id={rid!r} email_present={bool(email)} found={bool(match)}", flush=True)
            if not match: return self.send_json({'error':'RTI not found'},404)
            return self.send_json(public_rti(match))
        if self.path=='/api/response/analyse':
            scenario=body.get('scenario','highway')
            requested=body.get('request_items') or build_request(['actual expenditure','original and revised completion records'])
            response_text=body.get('response_text')
            if not response_text:
                if scenario=='highway':
                    response_text=('The authority confirms the sanctioned amount of ₹18.4 crore and the contractor ABC Infrastructure Ltd. '
                                    'The original completion date was 30 September 2024. The response does not provide expenditure incurred to date '
                                    'or a revised completion/extension order.')
                elif scenario=='passport':
                    response_text=('The passport application was received by the Regional Passport Office and is under verification. '
                                    'The response does not provide a complete file movement history or a recorded reason for delay.')
                else:
                    response_text='The authority response is limited and does not provide all requested records.'
            response_evidence=[{'id':f'RESPONSE-{scenario.upper()}-001','title':('Synthetic response — '+scenario),'page':'1','source_type':'Synthetic RTI response','text':response_text}]
            ai_meta={'mode':'fallback','model':None}
            if ai_enabled():
                try:
                    result,meta=ai_response_analyse(requested,response_text,scenario)
                    # Validate that live-model evidence is present; otherwise fall back rather than showing unsupported claims.
                    results=result['results']
                    if any('evidence' not in x for x in results):
                        raise RuntimeError('Response verifier returned a result without evidence field')
                    ai_meta={'mode':'live','model':meta['model'],'request_id':meta['request_id']}
                    print(f"[Jaano AI] live response verification model={meta['model']} request_id={meta['request_id']}",flush=True)
                except Exception as e:
                    print(f"[Jaano AI] live response verification failed; using fallback: {e}",flush=True)
                    results=[]
            else: results=[]
            if not results:
                if scenario=='highway':
                    results=[
                      {'question':requested[0] if len(requested)>0 else 'Actual expenditure','status':'unanswered','answer':'Not provided.','reason':'The response mentions the sanctioned amount but does not provide expenditure incurred to date.','evidence':[]},
                      {'question':requested[1] if len(requested)>1 else 'Revised completion / extension record','status':'unanswered','answer':'Not provided.','reason':'The response provides the original completion date but does not provide a revised completion or extension order.','evidence':[]}]
                elif scenario=='passport':
                    results=[
                      {'question':requested[0] if len(requested)>0 else 'Application processing status','status':'answered','answer':'Application received and under verification.','reason':'The response states the recorded processing stage.','evidence':[{'id':'RESPONSE-PASSPORT-001','page':'1','quote':'The passport application was received by the Regional Passport Office and is under verification.'}]},
                      {'question':requested[1] if len(requested)>1 else 'File movement/progress records','status':'unanswered','answer':'Not provided.','reason':'No file movement history is supplied.','evidence':[]},
                      {'question':requested[2] if len(requested)>2 else 'Recorded reason for delay','status':'unanswered','answer':'Not provided.','reason':'No recorded reason for delay is supplied.','evidence':[]}]
                else:
                    results=[{'question':x,'status':'unanswered','answer':'Not provided.','reason':'The synthetic response does not contain this information.','evidence':[]} for x in requested]
                appeal_draft='I am requesting a review of the response because the following information requested in my RTI has not been provided: ' + '; '.join(r['question'] for r in results if r['status']!='answered') + '.'
            else:
                appeal_draft=result['appeal_draft']
            answered=sum(1 for r in results if r['status']=='answered')
            unanswered=[r for r in results if r['status']!='answered']
            # Attach conservative evidence for any result that has a literal phrase match in the response.
            for item in results:
                if 'evidence' not in item: item['evidence']=[]
                if not item['evidence'] and item.get('status') in ('answered','partially_answered'):
                    terms=[w for w in item.get('answer','').split() if len(w)>4][:5]
                    quote=response_text[:240]
                    if terms and any(t.lower().strip('.,₹') in response_text.lower() for t in terms):
                        item['evidence']=[{'id':response_evidence[0]['id'],'page':'1','quote':quote}]
            return self.send_json({'results':results,'answered_count':answered,'unanswered':unanswered,'appeal_draft':appeal_draft,'ai':ai_meta,'response_text':response_text,'response_evidence':response_evidence})
        return self.send_json({'error':'not found'},404)

if __name__=='__main__':
    port=int(os.getenv('PORT','8000')); print(f'Jaano V11.2 running at http://localhost:{port}', flush=True); ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
