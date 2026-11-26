--!strict
-- Cosmetic local pool; caller provides factory/reset and MUST release once.
local Pool={}
function Pool.new(capacity: number,factory: ()->Instance,reset: (Instance)->())
    assert(capacity>=1 and capacity%1==0)
    local free: {Instance}={};local live: {[Instance]: boolean}={};local count=0;local closed=false
    local api={}
    function api.acquire(): Instance?
        if closed then return nil end
        local item=table.remove(free)
        if not item then if count>=capacity then return nil end;item=factory();count+=1 end
        live[item]=true;return item
    end
    function api.release(item: Instance): boolean
        if not live[item] then return false end
        live[item]=nil
        local ok,err=pcall(reset,item)
        if not ok or closed then item:Destroy();count-=1;if not ok then warn(err) end
        else item.Parent=nil;table.insert(free,item) end
        return true
    end
    function api.destroy()
        if closed then return end;closed=true
        for item in live do item:Destroy() end
        for _,item in free do item:Destroy() end
        table.clear(live);table.clear(free);count=0
    end
    return api
end
return Pool
