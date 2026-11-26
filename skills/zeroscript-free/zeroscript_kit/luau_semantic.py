"""Bounded structural Luau review. Deliberately small statement subset, not a parser replacement.
Unknown expressions lose precision; unsupported control flow is explicitly reported.
"""
from collections import Counter, defaultdict
import re
from .luau_rules import finding, SINKS, YIELDS, RETRY_EFFECTS
from .luau_roblox import tokenize, WORD
GATES={
 'G39':('scope-shadow','Local binding shadows an active binding'),
 'G40':('scope-redeclare','Repeated declaration in the same lexical scope'),
 'G41':('global-write','Bare assignment without a known local binding'),
 'G42':('unused-binding','Local binding has no observed use'),
 'G43':('self-assignment','Trivial assignment to itself'),
 'G44':('unreachable-statement','Statement follows unconditional return in a supported block'),
 'G45':('return-contract','Annotated nonoptional function may fall through'),
 'G46':('nil-receiver','Known nil value used as member receiver'),
 'G47':('literal-arithmetic','Known nonnumeric literal participates in numeric arithmetic'),
 'G48':('division-zero','Literal division or modulo by zero'),
 'G49':('constant-branch','Literal boolean branch condition'),
 'G50':('duplicate-branch','Repeated adjacent conditional predicate'),
 'G51':('duplicate-key','Repeated literal table field in a simple constructor'),
 'G52':('recursive-call','Direct self-call without observed conditional branch'),
 'G53':('helper-remote-flow','Remote value reaches local helper effect summary'),
 'G54':('helper-retry-yield','Named local helper has possible retry callback yield'),
 'G55':('helper-retry-effect','Named local helper has possible retry callback side effect'),
 'G56':('connection-handle','Discarded direct Connect result'),
 'G57':('task-handle','Discarded delayed task handle'),
 'G58':('yield-after-check','Yield between simple guard and subsequent shared effect'),
 'G59':('numeric-finiteness','Remote numeric guard lacks observed finite-number check'),
 'G60':('structural-coverage','Unsupported structural form or analysis budget reached'),
}
IDENT=re.compile(r'^[A-Za-z_][A-Za-z_0-9]*$'); KEYWORDS=set('and break do else elseif end false for function if in local nil not or repeat return then true until while continue type export'.split())
MAX_LINES=12000;MAX_WORK=200000

def name(v):return isinstance(v,str) and IDENT.fullmatch(v) and v not in KEYWORDS

def rows(text):
    toks,flags,_=tokenize(text); d=defaultdict(list)
    for k,v,l in toks:
        # Literal content never becomes executable tokens; distinguish equal string keys.
        d[l].append(('STR:'+repr(v)) if k=='string' else v)
    return list(d.items()),flags

def inspect(path,text):
    lines,flags=rows(text);out=[];seen=set();coverage=Counter();work=0;unsupported_sites=defaultdict(list)
    def add(g,l,code,msg,identity):
        key=(g,l,code,str(identity))
        if key not in seen:
            seen.add(key);out.append(finding(g,path,l,code,msg,identity,'high' if g in ('G46','G53','G54','G55') else 'medium'))
    def unsupported(l,reason):
        coverage['unsupported']+=1
        if 'budget' in reason.lower():coverage['budget_exceeded']+=1
        unsupported_sites[reason].append(l)
    def finish():
        for reason,sites in sorted(unsupported_sites.items()):
            add('G60',sites[0],'unsupported_structure',f'{reason} ({len(sites)} sites; first lines {sites[:6]}).',(reason,len(sites)))
        return out,dict(coverage)
    if len(lines)>MAX_LINES:
        unsupported(1,'Structural line budget exceeded');return finish()
    # Independent literal checks do not rely on block parsing.
    for l,v in lines:
        for i,x in enumerate(v):
            if x in ('/','%') and i+1<len(v) and v[i+1] in ('0','0.0','0_0'):add('G48',l,'zero_divisor','Literal zero divisor; verify finite arithmetic.',v)
            if x in ('+','-','*','/','%') and i and i+1<len(v) and (v[i-1] in ('true','false','nil') or v[i+1] in ('true','false','nil')):add('G47',l,'literal_arithmetic','Nonnumeric literal in numeric expression.',v)
        if len(v)>=3 and v[0]=='if' and v[1] in ('true','false') and v[2]=='then':add('G49',l,'constant_condition','Literal condition; verify intended branch.',v[:3])
        if len(v)>=3 and name(v[0]) and v[1]=='=' and v[2:]==[v[0]]:add('G43',l,'self_assign','Assignment does not change the binding.',v)
        # Only flat, single-line table constructor; no nested field ambiguity.
        if v.count('{')==1 and v.count('}')==1:
            a,b=v.index('{'),v.index('}');keys=[]
            for i in range(a+1,b-1):
                if v[i-1] in ('{',',',';') and name(v[i]) and v[i+1]=='=':keys.append(v[i])
            for k,n in Counter(keys).items():
                if n>1:add('G51',l,'duplicate_table_key','Repeated literal field overwrites earlier value.',k)
        if len(v)>4 and name(v[0]) and v[1] in ('.',':') and v[2] in ('Connect','ConnectParallel') and v[3]=='(':add('G56',l,'discarded_connection','Connection handle is discarded; verify owner teardown.',v[:4])
        if v[:4]==['task','.','delay','(']:add('G57',l,'discarded_delay','Delayed task handle discarded; verify cancellation or bounded lifetime.',v[:4])
    # Identify simple named local function and inline callback regions with balanced
    # line-oriented blocks. One-line bodies, loops, nested functions and multiline
    # statements are deliberately excluded from flow rather than guessed.
    regions=[];i=0
    def header(v):
        if v[:2]==['local','function'] and len(v)>4 and name(v[2]) and v[3]=='(':return ('named',v[2],3)
        if v[:1]==['function'] and '(' in v:
            j=v.index('(');parts=v[1:j]
            if parts and name(parts[0]) and all(name(x) if i%2==0 else x in ('.',':') for i,x in enumerate(parts)) and len(parts)%2==1:return ('qualified',''.join(parts),j)
        if 'function' in v:
            j=v.index('function')
            if j+1<len(v) and v[j+1]=='(' and any(x in v[:j] for x in ('OnServerEvent','OnServerInvoke','UpdateAsync')):return ('retry' if 'UpdateAsync' in v[:j] else 'remote','',j+1)
        return None
    while i<len(lines):
        l,v=lines[i];h=header(v)
        if not h:
            if 'function' in v:unsupported(l,'Function form outside structural subset')
            i+=1;continue
        kind,fn,opening=h
        try:closing=v.index(')',opening)
        except ValueError:unsupported(l,'Multiline function header');i+=1;continue
        params=v[opening+1:closing];names=['self'] if kind=='qualified' and ':' in fn else [];ok=True
        for chunk in ' '.join(params).split(',') if params else []:
            p=chunk.strip().split(' ')
            if not p or not name(p[0]) or len(p)>1 and p[1]!=':':ok=False;break
            names.append(p[0])
        tail=v[closing+1:];annotation=tail[1:] if tail[:1]==[':'] else []
        if not ok or tail and not (kind in ('named','qualified') and tail[:1]==[':'] and len(tail)==2 and name(tail[1])):
            unsupported(l,'Unsupported parameter or inline function body');i+=1;continue
        blocks=['function'];j=i+1;valid=True
        while j<len(lines):
            z=lines[j][1];work+=len(z)
            if work>MAX_WORK:unsupported(l,'Region discovery work budget');return finish()
            if z[:1]==['if'] and z[-1:]==['then']:blocks.append('if')
            elif z[:1] in (['for'],['while']) and z[-1:]==['do']:blocks.append('loop')
            elif z==['do']:blocks.append('do')
            elif z==['repeat']:blocks.append('repeat')
            elif z[:1]==['until']:
                if blocks[-1]!='repeat':valid=False;break
                blocks.pop()
            elif z[:1]==['end']:
                if blocks[-1]=='repeat':valid=False;break
                blocks.pop()
                if not blocks:break
                if z!=['end']:valid=False
            elif any(x in z for x in ('function','for','while','repeat','until','do','then')) and z[:1] not in (['elseif'],):valid=False
            j+=1
        if j==len(lines) or not valid or blocks:
            unsupported(l,'Unsupported nested function or compound block');i+=1;continue
        regions.append((kind,fn,l,names,annotation,lines[i+1:j]));i=j+1
    # Summaries conservatively propagate observed effect names through unique local
    # named helpers. This is name-based, not alias or module resolution.
    count=Counter(r[1] for r in regions if r[0]=='named');summaries={};calls={}
    for kind,fn,l,params,annotation,body in regions:
        if kind!='named' or count[fn]!=1:continue
        ns={x for _,v in body for j,x in enumerate(v[:-1]) if name(x) and v[j+1]=='('};summaries[fn]=set(ns & (SINKS|YIELDS|RETRY_EFFECTS));calls[fn]=ns
    for _ in range(len(summaries)+1):
        changed=False
        for fn in summaries:
            old=len(summaries[fn]);summaries[fn].update(*(summaries[x] for x in calls[fn] if x in summaries));changed|=len(summaries[fn])!=old
            work+=len(calls[fn])+1
            if work>MAX_WORK:unsupported(1,'Helper summary work budget');return finish()
        if not changed:break
    for kind,fn,line,params,annotation,body in regions:
        coverage['supported_regions']+=1
        # A flat stack tracks declarations and per-block return reachability. At
        # branch joins, mutable facts become unknown (soundly lose precision).
        scopes=[{p:{'line':line,'value':'unknown','used':False,'taint':kind=='remote' and k>0,'param':True} for k,p in enumerate(params)}];dead=[False];conditions=[];branch_returns=[];block_types=[];guard=False;yielded=False;finite=False;numeric=False
        def get(n):return next((s[n] for s in reversed(scopes) if n in s),None)
        def used(v):
            for j,x in enumerate(v):
                if name(x) and (j==0 or v[j-1] not in ('.',':')):
                    b=get(x)
                    if b:b['used']=True
        def close_scope():
            for n,b in scopes.pop().items():
                if not b['used'] and not b['param'] and not n.startswith('_'):add('G42',b['line'],'unused_local','No observed use in supported lexical block.',n)
            return dead.pop()
        def reset():
            for s in scopes:
                for b in s.values():b['value']='unknown';b['taint']=b['taint'] or b.get('ever_tainted',False)
        for l,v in body:
            if not v:continue
            work+=len(v)
            if work>MAX_WORK:unsupported(l,'Flow work budget');return finish()
            if v==['end'] or v[0]=='until':
                if len(scopes)>1:
                    if v[0]=='until':used(v[1:])
                    ended=close_scope();c=conditions.pop();returns=branch_returns.pop();typ=block_types.pop();reset()
                    # An if with an else and every branch returning cannot fall through.
                    if typ=='if_else' and ended and all(returns):dead[-1]=True
                    elif typ=='do' and ended:dead[-1]=True
                else:unsupported(l,'Unmatched end')
                continue
            if v[0] in ('else','elseif'):
                if len(scopes)<=1 or block_types[-1] not in ('if','if_else'):unsupported(l,'Unmatched branch');continue
                branch_returns[-1].append(close_scope());reset();scopes.append({});dead.append(dead[-1])
                if v[0]=='elseif':
                    used(v[1:-1])
                    if v[1:-1]==conditions[-1]:add('G50',l,'duplicate_predicate','Repeated adjacent predicate.',v)
                    conditions[-1]=v[1:-1]
                else:block_types[-1]='if_else'
                continue
            if (v[0]=='if' and v[-1]=='then') or (v[0] in ('for','while') and v[-1]=='do') or v in (['do'],['repeat']):
                typ='if' if v[0]=='if' else 'do' if v==['do'] else 'repeat' if v==['repeat'] else 'loop'
                if dead[-1]:add('G44',l,'after_return','Block follows unconditional return in this supported scope.',v)
                used(v[1:-1]);conditions.append(v[1:-1]);branch_returns.append([]);block_types.append(typ);scopes.append({});dead.append(dead[-1]);guard=True
                if v[0]=='for':
                    stop=next((i for i,x in enumerate(v) if x in ('in','=')),0)
                    for n in v[1:stop]:
                        if name(n):scopes[-1][n]={'line':l,'value':'unknown','taint':False,'used':False,'param':True}
                numeric|=any(x in v for x in ('type','typeof')) and any(x=="STR:'number'" for x in v)
                finite|=any(x in v for x in ('isfinite','isFinite','huge'))
                continue
            if dead[-1]:add('G44',l,'after_return','Statement follows unconditional return in this supported block.',v);continue
            if v[0]=='return':used(v[1:]);dead[-1]=True;continue
            if v[0]=='local' and (len(v)<2 or not name(v[1]) or len(v)>2 and v[2]!='='):
                unsupported(l,'Local declaration outside single-binding subset');reset();continue
            decl=v[0]=='local' and len(v)>1 and name(v[1]) and (len(v)==2 or v[2]=='=')
            assign=len(v)>2 and name(v[0]) and v[1]=='='
            rhs=v[3:] if decl else v[2:] if assign else v
            for k,x in enumerate(rhs[:-1]):
                if name(x) and rhs[k+1] in ('.',':','[') and (b:=get(x)) and b['value']=='nil':add('G46',l,'nil_member','Known nil local used as member receiver.',x)
            if decl or assign:
                n=v[1] if decl else v[0];existing=get(n);used(rhs)
                val='nil' if not rhs or rhs==['nil'] else get(rhs[0])['value'] if len(rhs)==1 and get(rhs[0]) else 'unknown'
                taint=any(get(x) and get(x)['taint'] for x in rhs if name(x))
                if decl:
                    if n in scopes[-1]:add('G40',l,'local_redeclare','Same-scope local redeclaration.',n)
                    elif existing:add('G39',l,'local_shadow','Local shadows an outer binding.',n)
                    scopes[-1][n]={'line':l,'value':val,'taint':taint,'used':False,'param':False}
                elif existing:existing.update(value=val,taint=taint,ever_tainted=existing.get('ever_tainted',False) or existing['taint'] or taint)
                else:add('G41',l,'bare_write','Bare write has no resolved local in this region; inspect outer/global ownership.',n)
            else:used(v)
            for k,x in enumerate(v[:-1]):
                if not name(x) or v[k+1]!='(':continue
                effects=summaries.get(x,set());direct=x in YIELDS
                if kind=='remote' and effects&SINKS and any(get(y) and get(y)['taint'] for y in v[k+2:] if name(y)):add('G53',l,'remote_helper_effect','Untrusted local reaches helper with observed effect calls; trace argument-to-effect path.',(x,sorted(effects&SINKS)))
                if kind=='retry' and effects&YIELDS:add('G54',l,'retry_helper_yield','Helper may yield inside retryable transform.',(x,sorted(effects&YIELDS)))
                if kind=='retry' and effects&RETRY_EFFECTS:add('G55',l,'retry_helper_effect','Helper may repeat external effects inside retryable transform.',(x,sorted(effects&RETRY_EFFECTS)))
                if kind=='named' and x==fn and not guard:add('G52',l,'unguarded_self_call','Direct self-call before observed conditional guard.',fn)
                if guard and (direct or effects&YIELDS):yielded=True
                if yielded and (x in SINKS or effects&SINKS):add('G58',l,'yield_then_effect','Effect after a possible yield following a guard; revalidate shared state.',x)
        if kind in ('named','qualified') and annotation and annotation[0] not in ('nil','any','unknown') and not dead[0]:add('G45',line,'return_fallthrough','Annotated function may fall through; branch proof outside supported subset.',fn)
        if kind=='remote' and numeric and not finite:add('G59',line,'numeric_guard_review','Numeric type guard does not by itself reject NaN or infinity.',params)
        while scopes:close_scope()
    coverage['candidate_headers']=sum(bool(header(v)) for _,v in lines)
    coverage['uninspected_headers']=max(0,coverage['candidate_headers']-coverage['supported_regions'])
    if coverage['uninspected_headers'] and not coverage['unsupported']:unsupported(1,'Some candidate function headers not inspected')
    return finish()
