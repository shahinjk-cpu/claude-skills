--!strict
-- Local request generations for async UI/preview work. Not server authorization or cancellation of network calls.
local RequestEpoch = {}
function RequestEpoch.new()
    local epoch = 0
    local closed = false
    local api = {}
    function api.begin(): number
        assert(not closed, "RequestEpoch is closed")
        epoch += 1
        return epoch
    end
    function api.isCurrent(ticket: number): boolean
        return not closed and ticket == epoch and ticket > 0
    end
    function api.invalidate()
        epoch += 1
    end
    function api.close()
        closed = true
        epoch += 1
    end
    return api
end
return RequestEpoch
