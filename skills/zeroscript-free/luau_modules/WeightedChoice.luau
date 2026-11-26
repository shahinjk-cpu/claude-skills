--!strict
-- Deterministic seeded choice for free procedural content, NOT paid random-item compliance.
local Choice={}
export type Entry={id: string,weight: number}
function Choice.pick(entries: {Entry},rng: Random): string
    local total=0
    for _,e in entries do assert(e.weight>=0 and e.weight<math.huge);total+=e.weight end
    assert(total>0 and total<math.huge)
    local n=rng:NextNumber(0,total);local acc=0;local last=""
    for _,e in entries do
        if e.weight>0 then acc+=e.weight;last=e.id;if n<acc then return e.id end end
    end
    return last
end
return Choice
