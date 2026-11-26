--!strict
-- Stable slot offsets for client-side cosmetic followers. Index comes from server equipment order.
local Formation={}
function Formation.offset(index: number, columns: number, spacing: number, rowSpacing: number, firstRow: number): Vector3
    assert(index>=1 and index%1==0 and columns>=1 and columns%1==0 and spacing>0 and rowSpacing>0)
    local zero=index-1
    local row=math.floor(zero/columns)
    local col=zero%columns
    -- Roblox character forward is local -Z; positive Z is behind.
    return Vector3.new((col-(columns-1)/2)*spacing,0,firstRow+row*rowSpacing)
end
function Formation.alpha(dt: number, response: number): number
    assert(dt>=0 and response>=0)
    return 1-math.exp(-response*dt)
end
return Formation
