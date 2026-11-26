"""AEGIS gate engine: bounded token-based Roblox review, NOT semantic taint analysis.
Only literal/structural patterns are examined. A match is a review lead, never proof.
"""
from collections import Counter, defaultdict
import hashlib
from .luau_roblox import tokenize, WORD

# Stable IDs are a public report/policy interface. No gate silently approves security.
GATES = {
 'G01': ('source-integrity','Project source/config/tool stability'),
 'G02': ('syntax','Native Luau compilation'),
 'G03': ('types-lint','Native type checking and lint'),
 'G04': ('roblox-environment','Roblox definitions and instance context coverage'),
 'G05': ('type-policy','Strict mode and disabled type checking'),
 'G06': ('lexical-integrity','Lexical delimiter/string and directive review'),
 'G07': ('dependency-resolution','Unresolved literal module dependencies'),
 'G08': ('dependency-cycles','Strongly connected module components'),
 'G09': ('dependency-coverage','Dynamic, alias and unmapped requires'),
 'G10': ('dependency-complexity','Module fan-out and dependency chain depth'),
 'G11': ('dependency-boundaries','Client/shared to server-only module edges'),
 'G12': ('remote-authority','Remote handlers and trusted sender authority'),
 'G13': ('remote-input-flow','Direct remote argument or simple alias at effect sinks'),
 'G14': ('remote-validation','Inline remote callback validation marker coverage'),
 'G15': ('remote-rate','Inline remote callback rate-limit marker coverage'),
 'G16': ('remote-roundtrip','Server-to-client synchronous invocation'),
 'G17': ('execution-context','Client/server-only API usage'),
 'G18': ('receipt-ownership','Receipt callback ownership and purchase-finished events'),
 'G19': ('receipt-decision','Receipt acknowledgement and durable-grant review'),
 'G20': ('persistent-io','Persistent operation reliability and protected boundaries'),
 'G21': ('retry-yield','Explicit yielding calls inside inline UpdateAsync transforms'),
 'G22': ('retry-effects','External side effects inside inline UpdateAsync transforms'),
 'G23': ('protected-errors','Protected-call result and exception handling'),
 'G24': ('bounded-waits','Unbounded waits and blocking requests'),
 'G25': ('lifecycle','Signal, task and binding ownership'),
 'G26': ('frame-budget','Frame callbacks and expensive inline operations'),
 'G27': ('loop-budget','Unbounded loops and scheduler pressure'),
 'G28': ('parallel-context','Parallel callbacks and synchronization boundaries'),
 'G29': ('dynamic-code','Dynamic loading and opaque numeric requires'),
 'G30': ('asset-trust','External asset insertion'),
 'G31': ('http-trust','HTTP requests and external trust'),
 'G32': ('environment','Runtime environment mutation'),
 'G33': ('type-escapes','Explicit any casts and annotations'),
 'G34': ('destruction','Instance destruction and bulk deletion'),
 'G35': ('interaction-physics','Prompt, touch, click and network ownership authority'),
 'G36': ('legacy-scheduler','Legacy scheduling APIs'),
 'G37': ('replication-cost','Broad replication and unreliable transport review'),
 'G38': ('configuration','Analyzer configuration coverage and identity'),
}
LEGACY = {
 'typechecking_disabled':'G05','project_typechecking_disabled_candidate':'G05',
 'multiple_type_directives':'G06','late_type_directive':'G06','interpolated_string_review':'G06',
 'potential_remote_authority':'G12','remote_function_callback':'G12','server_invokes_client':'G16',
 'receipt_authority':'G18','purchase_finished_grant_candidate':'G18','persistent_write':'G20',
 'possible_silent_pcall':'G23','unbounded_wait':'G24','connection_lifetime':'G25',
 'frame_callback_candidate':'G26','unbounded_loop_candidate':'G27','dynamic_code':'G29',
 'external_asset_insert_candidate':'G30','external_http_candidate':'G31','environment_mutation_candidate':'G32',
 'possible_type_escape':'G33','destroy_candidate':'G34','client_interaction_authority':'G35',
 'network_ownership_candidate':'G35','legacy_scheduler_candidate':'G36',
}
for key in ('possible_client_api_in_server_source','possible_server_api_in_client_source',
            'possible_server_service_in_client_source','possible_client_service_in_server_source',
            'possible_client_localplayer_in_server_source'):
    LEGACY[key]='G17'

def legacy_gate(kind):
    if kind.startswith('unresolved_'):return 'G07'
    if kind=='relative_require_cycle':return 'G08'
    return LEGACY.get(kind,'G06')

def fp(*values):return hashlib.sha256(repr(values).encode()).hexdigest()[:32]

def finding(gate,path,line,code,message,identity,priority='medium'):
    return {'gate':gate,'path':path,'line':line,'code':code,'message':message,
            'priority':priority,'fingerprint':fp(gate,code,identity)}

def normalized(tokens):
    """Simple quoted bracket members only; do not confuse string values with syntax."""
    out=[];i=0
    while i<len(tokens):
        if (i+2<len(tokens) and out and (out[-1][0]=='name' or out[-1][:2] in [('symbol',')'),('symbol',']')])
            and tokens[i][:2]==('symbol','[') and tokens[i+1][0]=='string'
            and isinstance(tokens[i+1][1],str) and WORD.fullmatch(tokens[i+1][1])
            and tokens[i+2][:2]==('symbol',']')):
            out.extend([('symbol','.',tokens[i][2]),('name',tokens[i+1][1],tokens[i+1][2])]);i+=3
        else:out.append(tokens[i]);i+=1
    return out

# Effect sinks deliberately limited to identifiable call/member names. Receivers and
# shadowing are not semantically resolved; name matches remain candidates.
SINKS={'FireAllClients','FireClient','InvokeClient','SetAsync','UpdateAsync','IncrementAsync','RemoveAsync',
       'TakeDamage','Kick','Destroy','PivotTo','SetNetworkOwner','TeleportAsync','Grant','grant','give','award','GrantReward'}
YIELDS={'wait','Wait','WaitForChild','InvokeClient','InvokeServer','GetAsync','SetAsync','UpdateAsync',
        'IncrementAsync','RemoveAsync','RequestAsync','PostAsync','TeleportAsync','PreloadAsync'}
RETRY_EFFECTS=SINKS|{'PublishAsync','PromptProductPurchase','PromptGamePassPurchase','Play','spawn','defer','delay','Clone','Insert','insert'}
FRAME_COST={'GetDescendants','GetPlayers','GetTagged','Clone','Create','GetAsync','SetAsync','UpdateAsync','RequestAsync','PreloadAsync'}
PERSIST={'GetDataStore','GetOrderedDataStore','GetAsync','SetAsync','UpdateAsync','IncrementAsync','RemoveAsync','GetSortedAsync','ListKeysAsync'}
VALIDATORS={'type','typeof','assert','IsA','isfinite','isFinite','validate','Validate','validatePayload','validateRequest','validateInput','checkPayload'}
RATE={'rateLimit','RateLimit','allowRequest','AllowRequest','cooldown','Cooldown','consumeToken','ConsumeToken','throttle','Throttle','RequestGuard'}
MAX_CALLBACK_TOKENS=12000
MAX_CALLBACK_WORK=250000

class Tokens:
    def __init__(self,text):
        raw,self.flags,self.mode=tokenize(text);self.t=normalized(raw);self.v=[v if k!='string' else None for k,v,_ in self.t]
        self.pairs={};stack=[];opens={'(':')','[':']','{':'}'}
        for i,(k,v,_) in enumerate(self.t):
            if k!='symbol':continue
            if v in opens:stack.append((v,i))
            elif v in opens.values() and stack and opens[stack[-1][0]]==v:
                _,a=stack.pop();self.pairs[a]=i
        self.lines=defaultdict(list)
        for k,v,l in self.t:self.lines[l].append((k,v))
    def at(self,i):return self.v[i] if 0<=i<len(self.v) else None
    def member(self,i):return self.at(i-1) in ('.',':') and self.t[i][0]=='name'
    def call(self,i):return self.t[i][0]=='name' and self.at(i+1)=='(' and self.at(i-1)!='function'
    def names(self,a,b):return {v for k,v,_ in self.t[a:b] if k=='name'}
    def args(self,opening):
        """Split only by top-level comma; callers handle function-body ambiguity."""
        end=self.pairs.get(opening)
        if end is None:return []
        args=[];start=opening+1;i=start
        while i<end:
            if i in self.pairs:i=self.pairs[i]+1;continue
            if self.at(i)==',':args.append((start,i));start=i+1
            i+=1
        if start<end:args.append((start,end))
        return args
    def callback(self,opening):
        # Locate a direct inline function in the outer argument list (not in nested calls).
        end=self.pairs.get(opening)
        if end is None:return None
        i=opening+1
        while i<end:
            if self.at(i)=='function' and self.at(i+1)=='(' and (i==opening+1 or self.at(i-1)==','):
                pe=self.pairs.get(i+1)
                # Only callback-last call forms ending in `end)` (no semantic function parser).
                if pe is None or self.at(end-1)!='end':return None
                params=[]
                for a,b in self.args(i+1):
                    if a<b and self.t[a][0]=='name' and (b==a+1 or self.at(a+1)==':'):params.append(self.at(a))
                    else:return None
                return params,pe+1,end-1
            i=self.pairs[i]+1 if i in self.pairs else i+1
        return None

def inspect_source(path,text,context='unknown'):
    t=Tokens(text);out=[];seen=set();stats=Counter();work=0;receipt_assignments=[]
    def add(g,i,code,msg,priority='medium',identity=None):
        ln=t.t[i][2] if 0<=i<len(t.t) else 1
        key=(g,code,ln)
        if key in seen:return
        seen.add(key);out.append(finding(g,path,ln,code,msg,identity if identity is not None else t.lines[ln],priority))
    def inspect_callback(i,opening,kind):
        nonlocal work
        stats[kind+'_sites']+=1
        end=t.pairs.get(opening)
        if end is not None and (end-opening>MAX_CALLBACK_TOKENS or work+end-opening>MAX_CALLBACK_WORK):
            stats['callback_budget_exceeded']+=1;return
        cb=t.callback(opening)
        if cb is None:
            stats[kind+'_opaque']+=1
            # Existing authority/persistence/frame gates still cover the site.
            if kind=='remote':add('G14',i,'opaque_remote_handler','Callback not in supported direct-inline form; trace the actual handler and its validation.','high')
            elif kind=='retry':add('G21',i,'opaque_retry_transform','Trace the named or indirect UpdateAsync transform for yielding calls and repeated effects.','high')
            return
        params,a,b=cb
        if b-a>MAX_CALLBACK_TOKENS or work+b-a>MAX_CALLBACK_WORK:
            stats['callback_budget_exceeded']+=1;return
        work+=b-a;stats[kind+'_inspected']+=1
        names=t.names(a,b)
        if kind=='remote':
            untrusted=set(params[1:]) # first argument is engine-supplied Player
            if not params:add('G12',i,'sender_parameter_missing','Review missing explicit sender parameter; ensure server-derived identity.','high')
            if untrusted and not (names&VALIDATORS):add('G14',i,'no_local_validation_marker','No recognized validation marker in this inline callback. External validation may exist; trace every untrusted value.','high')
            if not names&RATE:add('G15',i,'no_local_rate_marker','No recognized rate-limit marker in this inline callback. Establish server-side request budget.','high')
            # Conservative forward scan of simple local aliases, no CFG, no claims of sanitization.
            aliases=set(untrusted)
            for j in range(a,b):
                if t.at(j)=='local' and t.at(j+2)=='=' and t.at(j+3) in aliases and t.t[j+1][0]=='name':aliases.add(t.at(j+1))
                if t.at(j) in SINKS and t.call(j):
                    e=t.pairs.get(j+1)
                    if e is not None and e<=b and e-j<=512:
                        touched=t.names(j+2,e)&aliases
                        if t.member(j) and t.at(j-2) in aliases:touched.add(t.at(j-2))
                        if touched:add('G13',j,'remote_argument_at_effect','Remote parameter/simple alias appears in effect receiver or arguments; trace validation, ownership and server-derived values.','high', (t.at(j),sorted(touched),t.lines[t.t[j][2]]))
                if t.member(j) and t.at(j+1) in ('=','+=','-=','*=','/='):
                    # A property assignment's immediate value or receiver only.
                    # Do not claim dataflow through arbitrary expressions or helpers.
                    touched={x for x in (t.at(j-2),t.at(j+2)) if x in aliases}
                    if touched:add('G13',j,'remote_argument_at_property_write','Remote parameter/simple alias is the immediate receiver or value of a property assignment; trace authoritative ownership and validation.','high',(t.at(j),sorted(touched),t.lines[t.t[j][2]]))
        elif kind=='retry':
            for j in range(a,b):
                if not t.call(j):continue
                name=t.at(j)
                if name in YIELDS:add('G21',j,'retry_yield_candidate','Potential yielding call within inline UpdateAsync transform. DataStore transforms cannot yield.','high')
                if name in RETRY_EFFECTS:add('G22',j,'retry_effect_candidate','Potential side effect within retryable transform; keep effects outside the transform or prove idempotency.','high')
        elif kind=='frame':
            for j in range(a,b):
                if t.call(j) and t.at(j) in FRAME_COST:add('G26',j,'frame_expensive_call','Potential expensive call inside frame callback; profile, cache, throttle or move work off frame path.')
    for i,(k,v,_) in enumerate(t.t):
        if k!='name':continue
        member=t.member(i);call=t.call(i)
        if member and v=='OnServerEvent' and t.at(i+1) in ('.',':') and t.at(i+2) in ('Connect','Once','ConnectParallel') and t.at(i+3)=='(':
            inspect_callback(i,i+3,'remote')
        if member and v=='OnServerInvoke' and t.at(i+1)=='=':
            stats['remote_sites']+=1;stats['remote_opaque']+=1
            add('G14',i,'remote_function_trace','Trace assigned RemoteFunction handler, including validation, authorization and rate limiting.','high')
        if member and v=='UpdateAsync' and call:inspect_callback(i,i+1,'retry')
        if member and v in ('Heartbeat','RenderStepped','PreRender','PreSimulation','PostSimulation','Stepped') and t.at(i+1) in ('.',':') and t.at(i+2) in ('Connect','Once','ConnectParallel') and t.at(i+3)=='(':
            inspect_callback(i,i+3,'frame')
        if member and v=='BindToRenderStep' and call:inspect_callback(i,i+1,'frame')
        if member and v=='ProcessReceipt' and t.at(i+1)=='=':
            receipt_assignments.append(t.t[i][2]);add('G19',i,'receipt_grant_trace','Trace durable PurchaseId-idempotent grant before PurchaseGranted; uncertain outcomes must not acknowledge.','high')
        if v=='PurchaseGranted' and member:add('G19',i,'purchase_granted_candidate','Verify this acknowledgement follows a durable successful or previously recorded grant.','high')
        if member and v in PERSIST and call:
            add('G20',i,'persistent_operation','Review service identity, pcall/error path, budgets, retries and stale session handling.','high')
        if member and v in ('InvokeServer','Wait','GetAsync') and call:add('G24',i,'yielding_boundary','Potential yielding call; inspect lifetime, cancellation and timeout strategy.')
        if member and v in ('Once','ConnectParallel','BindToRenderStep') and call:add('G25',i,'owned_binding','Verify owner, teardown, cancellation and unbinding.')
        if v in ('spawn','defer','delay') and member and t.at(i-2)=='task' and call:add('G25',i,'owned_task','Verify task ownership, cancellation and captured instance lifetime.')
        if member and v in ('ConnectParallel','desynchronize','synchronize') and call:add('G28',i,'parallel_boundary','Verify Actor context, API thread-safety and synchronization before unsafe mutations.','high')
        if member and v=='ClearAllChildren' and call:add('G34',i,'bulk_destruction','Verify ownership and impact before bulk cleanup.')
        if member and v=='FireAllClients' and call:add('G37',i,'broad_replication','Review recipient scope, payload size and frequency; avoid broad replication for private state.')
        if member and v=='new' and t.at(i-2)=='Instance' and call and i+2<len(t.t) and t.t[i+2][:2]==('string','UnreliableRemoteEvent'):
            add('G37',i,'unreliable_transport','Unreliable transport is unordered and lossy; do not use as sole authority for durable state.','high')
    return out,dict(stats),receipt_assignments


def strongly_connected(edges):
    """Iterative Kosaraju, deterministic, O(V+E) apart from sorting."""
    graph={n:sorted(set(d for d in ds if d in edges)) for n,ds in edges.items()};rev={n:[] for n in graph}
    for n,ds in graph.items():
        for d in ds:rev[d].append(n)
    seen=set();order=[]
    for n in sorted(graph):
        if n in seen:continue
        seen.add(n);stack=[(n,iter(graph[n]))]
        while stack:
            a,it=stack[-1];b=next(it,None)
            if b is None:order.append(a);stack.pop()
            elif b not in seen:seen.add(b);stack.append((b,iter(graph[b])))
    seen=set();components=[]
    for n in reversed(order):
        if n in seen:continue
        seen.add(n);stack=[n];group=[]
        while stack:
            a=stack.pop();group.append(a)
            for b in rev[a]:
                if b not in seen:seen.add(b);stack.append(b)
        components.append(sorted(group))
    # Kosaraju order is source -> sink on condensation DAG.
    owner={n:i for i,c in enumerate(components) for n in c};depth=[1]*len(components)
    for i in reversed(range(len(components))):
        children={owner[d] for n in components[i] for d in graph[n] if owner[d]!=i}
        if children:depth[i]=1+max(depth[j] for j in children)
    return {'components':components,'cycles':[c for c in components if len(c)>1 or c[0] in graph[c[0]]],
            'max_component_chain':max(depth,default=0),'fanout':{n:len(ds) for n,ds in graph.items()},'edge_count':sum(map(len,graph.values()))}
