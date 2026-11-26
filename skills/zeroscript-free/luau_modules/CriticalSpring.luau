--!strict
-- Exact critically damped scalar/vector spring for a constant target over dt.
-- Use one writer per visual channel; this is not a physics or damage simulation.
local Spring = {}
function Spring.step(x: number, velocity: number, target: number, omega: number, dt: number): (number, number)
    assert(omega > 0 and omega < math.huge and dt >= 0 and dt < math.huge)
    local offset = x-target
    local j = velocity+omega*offset
    local decay = math.exp(-omega*dt)
    return target + (offset+j*dt)*decay, (velocity-omega*j*dt)*decay
end
function Spring.vector(x: Vector3, v: Vector3, target: Vector3, omega: number, dt: number): (Vector3, Vector3)
    local a,b=Spring.step(x.X,v.X,target.X,omega,dt)
    local c,d=Spring.step(x.Y,v.Y,target.Y,omega,dt)
    local e,f=Spring.step(x.Z,v.Z,target.Z,omega,dt)
    return Vector3.new(a,c,e),Vector3.new(b,d,f)
end
return Spring
