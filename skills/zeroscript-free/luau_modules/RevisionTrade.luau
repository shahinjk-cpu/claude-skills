--!strict
-- IN-MEMORY offer handshake only. Not durable escrow or an inventory transaction.
-- Server caller validates ownership, reservations, state, and durable recovery before committing.
local Trade = {}
type Offer = {string}
function Trade.new(a: number,b: number,maxItems: number)
    assert(a~=b and maxItems>=1 and maxItems<=100)
    local revision=0
    local offers: {[number]: Offer} = {[a]={},[b]={}}
    local confirmed: {[number]: number} = {}
    local closed=false
    local api={}
    function api.setOffer(user: number, items: Offer): boolean
        if closed or not offers[user] or #items>maxItems then return false end
        local seen: {[string]: boolean}={}
        for _,id in ipairs(items) do
            if type(id)~="string" or #id==0 or #id>100 or seen[id] then return false end
            seen[id]=true
        end
        offers[user]=table.clone(items); revision+=1;table.clear(confirmed)
        return true
    end
    function api.confirm(user: number,rev: number): boolean
        if closed or not offers[user] or rev~=revision then return false end
        confirmed[user]=rev;return true
    end
    function api.snapshot()
        return {revision=revision,a=table.clone(offers[a]),b=table.clone(offers[b]),aConfirmed=confirmed[a]==revision,bConfirmed=confirmed[b]==revision}
    end
    function api.lockForCommit(rev: number): boolean
        if closed or rev~=revision or confirmed[a]~=revision or confirmed[b]~=revision then return false end
        closed=true;return true
    end
    function api.close() closed=true;table.clear(confirmed) end
    return api
end
return Trade
