"""Conservative Roblox source review. Token inspection, NOT an AST or taint analysis.
Only literal require edges are resolved; unknown dynamic dependencies stay unknown.
"""
import hashlib
import re
from pathlib import Path
from collections import Counter

LONG=re.compile(r'\[(=*)\[')
WORD=re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
NUMBER=re.compile(r'(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|(?:\d[\d_]*(?:\.(?!\.)[\d_]*)?|\.\d[\d_]*)(?:[eE][+-]?\d[\d_]*)?)')
DIRECTIVE=re.compile(r'^\s*--!\s*(strict|nonstrict|nocheck)\s*$')
MAX_TOKENS=250_000

# Token triples match the historical scanner interface. String values are literal
# contents only for uncomplicated literals; escapes are intentionally unresolved.
def tokenize(text):
    tokens=[]; flags=[]; directives=[]; i=0; line=1; started=False
    def emit(k,v,ln):
        if len(tokens)>=MAX_TOKENS: raise ValueError('lexical token budget exceeded')
        tokens.append((k,v,ln))
    def step(end):
        nonlocal i,line
        line+=text.count('\n',i,end); i=end
    def flag(kind,ln=None): flags.append((kind,line if ln is None else ln))
    def long_literal(start):
        m=LONG.match(text,start)
        if not m:return None
        end=text.find(']'+m[1]+']',m.end())
        if end<0:flag('unterminated_long_literal');return len(text),None
        return end+len(m[1])+2,text[m.end():end]
    def quoted():
        q=text[i]; ln=line; start=i+1; j=start; escaped=False
        while j<len(text):
            c=text[j]
            if c=='\\':
                escaped=True;j+=1
                if j<len(text) and text[j]=='z':
                    j+=1
                    while j<len(text) and text[j].isspace():j+=1
                elif text[j:j+2]=='\r\n':j+=2
                else:j+=1
                continue
            if c==q:
                emit('string',None if escaped else text[start:j],ln);step(j+1);return
            if c in '\r\n':break
            j+=1
        flag('unterminated_string',ln);emit('string',None,ln);step(min(j,len(text)))
    def interpolation(depth):
        ln=line;flag('interpolated_string_review',ln);emit('string',None,ln);step(i+1)
        while i<len(text):
            c=text[i]
            if c=='\\':step(min(len(text),i+2));continue
            if c=='`':step(i+1);return
            if c=='{':
                emit('symbol','{',line);step(i+1)
                if not code(depth+1,True):flag('unterminated_interpolation',ln);return
            else:step(i+1)
        flag('unterminated_interpolation',ln)
    def code(depth=0,inside=False):
        nonlocal started
        if depth>32:raise ValueError('interpolation nesting budget exceeded')
        braces=0
        while i<len(text):
            c=text[i]; ln=line
            if c.isspace():step(i+1);continue
            if text.startswith('--',i):
                item=long_literal(i+2)
                if item is not None:step(item[0]);continue
                end=text.find('\n',i);end=len(text) if end<0 else end
                m=DIRECTIVE.fullmatch(text[i:end]);
                if m:
                    if started:flag('late_type_directive',ln)
                    else:directives.append((m[1],ln))
                step(end);continue
            started=True
            item=long_literal(i)
            if item is not None:emit('string',item[1],ln);step(item[0]);continue
            if c in ('"',"'"):quoted();continue
            if c=='`':interpolation(depth);continue
            if inside and c=='}' and braces==0:
                emit('symbol',c,ln);step(i+1);return True
            if c=='{':braces+=1
            elif c=='}':braces-=1
            m=WORD.match(text,i) or NUMBER.match(text,i)
            if m:emit('name' if WORD.fullmatch(m[0]) else 'number',m[0],ln);step(m.end());continue
            op=next((op for op in ('...','..=','==','~=','<=','>=','::','->','+=','-=','*=','/=','..') if text.startswith(op,i)),c)
            emit('symbol',op,ln);step(i+len(op))
        return not inside
    code()
    modes={m for m,_ in directives}
    if len(directives)>1:flag('multiple_type_directives',directives[-1][1])
    # Do not certify conflicting directives as strict. Nocheck anywhere in the
    # header is conservative; the real compiler is responsible for exact semantics.
    mode='nocheck' if 'nocheck' in modes else next(iter(modes)) if len(modes)==1 else 'default'
    return tokens,flags,mode

# Priority means inspect earlier, never a verified vulnerability severity.
RULES={
 'dynamic_code':('high','Avoid runtime code loading; review authorized source and replace opaque numeric asset requires with reviewed local modules.'),
 'potential_remote_authority':('high','Trace sender-derived identity, type/finite/range checks, ownership, state, cooldown and server-side commit before effects.'),
 'remote_function_callback':('high','Validate untrusted arguments and bound work; return explicit errors without trusting client results.'),
 'server_invokes_client':('high','Avoid waiting on an untrusted client for authoritative decisions; use asynchronous messages where appropriate.'),
 'receipt_authority':('high','Grant idempotently by PurchaseId on the server; return NotProcessedYet if durable grant is uncertain.'),
 'purchase_finished_grant_candidate':('high','Purchase-finished signals are not proof of developer-product receipt fulfillment; audit actual grant authority.'),
 'persistent_write':('high','Validate plain data, use protected calls, handle budgets/conflicts and avoid non-idempotent effects in retryable transforms.'),
 'external_http_candidate':('high','Review URL ownership, response validation, credential handling, timeouts and server-only trust boundaries.'),
 'external_asset_insert_candidate':('high','Review permissions, provenance and inserted script descendants before parenting assets.'),
 'environment_mutation_candidate':('high','Review runtime environment manipulation; prefer explicit dependencies.'),
 'typechecking_disabled':('high','Do not hide errors with nocheck; verify actual analyzer coverage.'),
 'possible_client_api_in_server_source':('high','Verify Script.RunContext and instance placement; move client-only behavior to client code.'),
 'possible_server_api_in_client_source':('high','Verify execution context; server APIs and authoritative writes belong on the server.'),
 'possible_server_service_in_client_source':('high','Keep persistent storage and private services server-side; expose a validated public read model.'),
 'possible_client_service_in_server_source':('high','Check client-only API ownership and actual execution context.'),
 'possible_client_localplayer_in_server_source':('high','Use the trusted Player argument on the server; LocalPlayer is client-only.'),
 'client_interaction_authority':('high','Check distance, permissions, state and rate on the server even for prompt/click/touch events.'),
 'network_ownership_candidate':('high','Review authority and exploit impact of client-owned physics; verify ownership changes on server.'),
 'unbounded_wait':('medium','Bound uncertain WaitForChild calls and explicitly handle timeout; inspect streaming and initialization order.'),
 'connection_lifetime':('medium','Identify the owner and disconnect/destroy on teardown; persistent singleton listeners may be intentional.'),
 'possible_silent_pcall':('medium','Check success and error result; handle failure explicitly; do not hide exceptions.'),
 'legacy_scheduler_candidate':('medium','Prefer task APIs when equivalent, preserving scheduling semantics.'),
 'unbounded_loop_candidate':('medium','Inspect cancellation, yielding, per-frame work and termination; do not assume a busy loop from tokens alone.'),
 'possible_type_escape':('medium','Review explicit any casts/annotations around untrusted values; narrow and validate at boundaries.'),
 'destroy_candidate':('medium','Check ownership, references and lifecycle before deletion.'),
 'frame_callback_candidate':('medium','Audit work budget and disconnect/unbind when the owner ends.'),
 'multiple_type_directives':('high','Use one unambiguous type-mode directive; confirm analyzer interpretation.'),
 'late_type_directive':('medium','Place mode directive in the source header; verify actual analyzer mode.'),
 'interpolated_string_review':('low','Executable interpolation expressions were tokenized; inspect dynamic or nested behavior using the real analyzer.'),
}

def review_text(text,context='unknown'):
    tokens,flags,mode=tokenize(text)
    # Treat simple bracket member access like dotted access; escaped/dynamic keys stay unresolved.
    normalized=[];j=0
    while j<len(tokens):
        if j+2<len(tokens) and normalized and (normalized[-1][0]=='name' or normalized[-1][1] in (')',']')) and tokens[j][1]=='[' and tokens[j+1][0]=='string' and isinstance(tokens[j+1][1],str) and WORD.fullmatch(tokens[j+1][1]) and tokens[j+2][1]==']':
            normalized.extend([('symbol','.',tokens[j][2]),('name',tokens[j+1][1],tokens[j+1][2])]);j+=3
        else:normalized.append(tokens[j]);j+=1
    tokens=normalized
    findings=[];seen=set(); line_tokens={}
    for k,v,ln in tokens:line_tokens.setdefault(ln,[]).append((k,v))
    def add(kind,ln):
        if (kind,ln) in seen:return
        seen.add((kind,ln));priority,advice=RULES.get(kind,('medium','Inspect source and verify with the actual Luau compiler.'))
        # Content-bound identity ignores whitespace and line movement but retains literal changes.
        fingerprint=hashlib.sha256(repr((kind,line_tokens.get(ln,[]))).encode()).hexdigest()[:24]
        findings.append({'line':ln,'kind':kind,'severity':'review','priority':priority,'advice':advice,'fingerprint':fingerprint})
    for kind,ln in flags:add(kind,ln)
    if mode=='nocheck':add('typechecking_disabled',1)
    stack=[];opens={'(':')','[':']','{':'}'};closes=set(opens.values());requires=[];instance_requires=[];unknown_requires=0
    for i,(typ,v,ln) in enumerate(tokens):
        if typ=='symbol':
            if v in opens:stack.append((v,ln))
            elif v in closes:
                if not stack or opens[stack[-1][0]]!=v:add('possible_unbalanced_delimiter',ln)
                else:stack.pop()
        if typ!='name':continue
        before=tokens[i-1][1] if i else None
        tail=tokens[i+1:i+5]; after=[t[1] for t in tail]; call=after[:1]==['(']; member=before in ('.',':')
        if v=='loadstring' and call:add('dynamic_code',ln)
        if v=='require' and not member and before!='function' and call and len(tail)>1:
            if tail[1][0]=='number':add('dynamic_code',ln)
            if tail[1][0]=='string' and tail[1][1] is not None and after[2:3]==[')']:
                requires.append({'line':ln,'literal':tail[1][1]})
            elif tail[1][0]!='number':
                # Limited static Roblox paths: require(script.Parent.X),
                # require(game:GetService("ReplicatedStorage").X), require(game.X.Y).
                j=i+2;base=tokens[j][1];parts=[]
                if base in ('script','game') and tokens[j][0]=='name':
                    j+=1
                    if base=='game' and j+4<len(tokens) and [t[1] for t in tokens[j:j+3]]==[':','GetService','('] and tokens[j+3][0]=='string' and isinstance(tokens[j+3][1],str) and tokens[j+4][1]==')':
                        parts.append(tokens[j+3][1]);j+=5
                    while j+1<len(tokens) and tokens[j][1]=='.' and tokens[j+1][0]=='name':
                        parts.append(tokens[j+1][1]);j+=2
                    if parts and j<len(tokens) and tokens[j][1]==')':instance_requires.append({'line':ln,'base':base,'parts':parts})
                    else:unknown_requires+=1
                else:unknown_requires+=1
        if member and v=='OnServerEvent':add('potential_remote_authority',ln)
        if member and v=='OnServerInvoke':add('remote_function_callback',ln)
        if member and v=='InvokeClient' and call:add('server_invokes_client',ln)
        if member and v=='ProcessReceipt':add('receipt_authority',ln)
        if member and v=='PromptProductPurchaseFinished':add('purchase_finished_grant_candidate',ln)
        if member and v in ('SetAsync','UpdateAsync','RemoveAsync','IncrementAsync') and call:add('persistent_write',ln)
        if member and v in ('GetAsync','PostAsync','RequestAsync') and call and v!='GetAsync':add('external_http_candidate',ln)
        if member and v in ('LoadAsset','LoadAssetVersion','LoadAssetAsync','GetObjects') and call:add('external_asset_insert_candidate',ln)
        if v in ('getfenv','setfenv') and call and not member:add('environment_mutation_candidate',ln)
        if v in ('wait','spawn','delay') and call and not member and before!='function':add('legacy_scheduler_candidate',ln)
        if member and v=='WaitForChild' and call and len(tail)>2 and tail[1][0]=='string' and after[2:3]==[')']:add('unbounded_wait',ln)
        if member and v=='Connect' and call:add('connection_lifetime',ln)
        if v in ('pcall','xpcall') and call and not member:add('possible_silent_pcall',ln)
        if member and v in ('Triggered','MouseClick','Touched'):add('client_interaction_authority',ln)
        if member and v in ('SetNetworkOwner','SetNetworkOwnershipAuto') and call:add('network_ownership_candidate',ln)
        if v=='while' and after[:2]==['true','do']:add('unbounded_loop_candidate',ln)
        if v=='any' and before in (':','::'):add('possible_type_escape',ln)
        if member and v=='Destroy' and call:add('destroy_candidate',ln)
        if member and v in ('RenderStepped','PreRender','Heartbeat','BindToRenderStep','Stepped'):add('frame_callback_candidate',ln)
        if context=='server' and member:
            if v in ('FireServer','InvokeServer') and call:add('possible_client_api_in_server_source',ln)
            if v=='LocalPlayer':add('possible_client_localplayer_in_server_source',ln)
            if v in ('BindToRenderStep','RenderStepped','PreRender'):add('possible_client_service_in_server_source',ln)
        if context=='client' and member:
            if v in ('FireClient','FireAllClients','InvokeClient','OnServerInvoke','OnServerEvent','SetNetworkOwner','SetNetworkOwnershipAuto','ProcessReceipt'):add('possible_server_api_in_client_source',ln)
            if v=='GetService' and call and len(tail)>1 and tail[1][0]=='string' and tail[1][1] in ('DataStoreService','MemoryStoreService','ServerStorage','ServerScriptService','MessagingService'):add('possible_server_service_in_client_source',ln)
    for _,ln in stack:add('possible_unclosed_delimiter',ln)
    return {'type_mode':mode,'findings':sorted(findings,key=lambda f:(f['line'],f['kind'])),'literal_requires':requires,'instance_requires':instance_requires,'unknown_require_calls':unknown_requires}

def relative_graph(rows,root,all_paths,instance_index=None):
    """Only unambiguous literal relative paths; never execute require."""
    graph={r['path']:[] for r in rows}; unresolved=[]; external=0
    for r in rows:
        for dep in r['literal_requires']:
            s=dep['literal']
            if not s.startswith(('./','../')):external+=1;continue
            p=(root/r['path']).parent/s
            candidates=[p] if p.suffix in ('.lua','.luau') else [Path(str(p)+x) for x in ('.luau','.lua')]+[p/'init.luau',p/'init.lua']
            hits=[]
            for c in candidates:
                c=c.resolve()
                if c.is_relative_to(root) and c.relative_to(root).as_posix() in all_paths:hits.append(c.relative_to(root).as_posix())
            if len(hits)==1:graph[r['path']].append(hits[0])
            else:unresolved.append({'path':r['path'],'line':dep['line'],'literal':s,'reason':'ambiguous' if hits else 'not found in scope'})
    instance_unresolved=[];instance_unknown=0
    if instance_index:
        paths_by_source,nodes=instance_index
        for r in rows:
            for dep in r.get('instance_requires',[]):
                current=() if dep['base']=='game' else paths_by_source.get(r['path'])
                if current is None:
                    instance_unknown+=1;continue
                for part in dep['parts']:
                    current=current[:-1] if part=='Parent' else current+(part,)
                hits=nodes.get(current,[])
                if len(hits)==1 and hits[0][0]=='ModuleScript' and hits[0][1] is not None:
                    graph[r['path']].append(hits[0][1])
                else:instance_unresolved.append({'path':r['path'],'line':dep['line'],'literal':dep['base']+'.'+'.'.join(dep['parts']),'reason':'unmapped, ambiguous or non-ModuleScript target'})
    else:instance_unknown=sum(len(r.get('instance_requires',[])) for r in rows)
    # Iterative traversal avoids recursion-depth crashes on large projects.
    state={};cycles=[]
    for start in graph:
        if start in state:continue
        stack=[(start,iter(graph[start]))];state[start]=1;active=[start]
        while stack:
            node,it=stack[-1]
            child=next(it,None)
            if child is None:state[node]=2;stack.pop();active.pop();continue
            if child not in graph:continue
            if state.get(child)==1:
                cycles.append(active[active.index(child):]+[child]);continue
            if child not in state:state[child]=1;active.append(child);stack.append((child,iter(graph[child])))
    return {'edges':graph,'cycles':cycles[:100],'unresolved':unresolved,'nonrelative_literals':external,'unresolved_instance_paths':instance_unresolved,'unmapped_instance_calls':instance_unknown,'unknown_require_calls':sum(r.get('unknown_require_calls',0) for r in rows),'scope':'literal relative require and limited static instance edges using supplied sourcemap; aliases, dynamic requires, and selected-out cycles not resolved'}
