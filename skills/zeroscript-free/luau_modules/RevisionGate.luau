--!strict
-- Local authoritative snapshot ordering; caller validates schema and applies state synchronously without yielding.
-- A new stream/session gets a new gate; do not reset just because an older packet arrives.
local RevisionGate = {}
local function valid(n: number): boolean
    return n >= 0 and n <= 9007199254740991 and n % 1 == 0
end
function RevisionGate.new()
    local latest: number? = nil
    local api = {}
    function api.snapshot(revision: number): boolean
        if not valid(revision) or (latest ~= nil and revision <= latest) then return false end
        latest = revision
        return true
    end
    function api.delta(base: number, revision: number): boolean
        if not valid(base) or not valid(revision) or latest == nil or base ~= latest or revision <= base then return false end
        latest = revision
        return true
    end
    function api.current(): number? return latest end
    return api
end
return RevisionGate
