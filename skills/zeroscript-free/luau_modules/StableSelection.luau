--!strict
-- Stable ID selection for client UI. Reconcile when authoritative inventory changes.
local Selection={}
function Selection.new()
    local selected: string?=nil
    local api={}
    function api.set(id: string?) selected=id end
    function api.get(): string? return selected end
    function api.reconcile(available: {[string]: boolean}): string?
        if selected and not available[selected] then selected=nil end
        return selected
    end
    return api
end
return Selection
