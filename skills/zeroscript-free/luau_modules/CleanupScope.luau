--!strict
-- LIFO teardown; individual cleanup failure cannot stop other callbacks.
local Scope={}
function Scope.new()
    local stack: {()->()}={};local closed=false
    local api={}
    function api.add(cleanup: ()->())
        if closed then local ok,err=pcall(cleanup);if not ok then warn(err) end else table.insert(stack,cleanup) end
    end
    function api.connection(conn: RBXScriptConnection) api.add(function() conn:Disconnect() end) end
    function api.instance(inst: Instance) api.add(function() inst:Destroy() end) end
    function api.close()
        if closed then return end;closed=true
        for i=#stack,1,-1 do local ok,err=pcall(stack[i]);if not ok then warn(err) end end
        table.clear(stack)
    end
    return api
end
return Scope
