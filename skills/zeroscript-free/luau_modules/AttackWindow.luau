--!strict
-- Per server-authorized attack lifetime. Caller validates target, LOS, teams and damage.
local Attack = {}
function Attack.new(startTime: number, activeStart: number, activeEnd: number, recoveryEnd: number)
    assert(activeStart>=0 and activeEnd>activeStart and recoveryEnd>=activeEnd and recoveryEnd<math.huge)
    local hits: {[Instance]: boolean}={}
    local canceled=false
    local api={}
    function api.phase(now: number): string
        if canceled then return "Canceled" end
        local t=now-startTime
        if t<activeStart then return "Startup" elseif t<activeEnd then return "Active" elseif t<recoveryEnd then return "Recovery" end
        return "Done"
    end
    function api.tryHit(target: Instance,now: number): boolean
        if api.phase(now)~="Active" or hits[target] then return false end
        hits[target]=true;return true
    end
    function api.cancel() canceled=true;table.clear(hits) end
    return api
end
return Attack
