--!strict
-- One bucket per authenticated server-side player/action. Caller must remove departed players.
local TokenBucket = {}
type Entry = {tokens: number, time: number}
function TokenBucket.new(capacity: number, refillPerSecond: number, clock: (() -> number)?)
    assert(capacity > 0 and capacity < math.huge and refillPerSecond >= 0 and refillPerSecond < math.huge)
    local now = clock or os.clock
    local entries: {[number]: Entry} = {}
    local api = {}
    function api.allow(userId: number, cost: number?): boolean
        local charge = cost or 1
        if not (charge > 0 and charge <= capacity) then return false end
        local t = now()
        local entry = entries[userId]
        if not entry then entry = {tokens=capacity,time=t}; entries[userId]=entry end
        entry.tokens = math.min(capacity, entry.tokens + math.max(0,t-entry.time)*refillPerSecond)
        entry.time = math.max(t,entry.time)
        if entry.tokens < charge then return false end
        entry.tokens -= charge
        return true
    end
    function api.remove(userId: number) entries[userId]=nil end
    function api.clear() table.clear(entries) end
    return api
end
return TokenBucket
