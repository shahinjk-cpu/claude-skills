--!strict
-- Segment sweep helper for server-owned projectiles; origin/velocity must already be validated.
local Sweep={}
function Sweep.segment(previous: Vector3,nextPosition: Vector3,ignore: {Instance},collisionGroup: string?): RaycastResult?
    local delta=nextPosition-previous
    if delta.Magnitude<=1e-6 then return nil end
    local params=RaycastParams.new()
    params.FilterType=Enum.RaycastFilterType.Exclude
    params.FilterDescendantsInstances=ignore
    if collisionGroup then params.CollisionGroup=collisionGroup end
    return workspace:Raycast(previous,delta,params)
end
return Sweep
