--!strict
-- Server-safe primitive guards. No side effects; validate context separately.
local Finite = {}
function Finite.number(value: any, minimum: number, maximum: number): boolean
    return type(value) == "number" and value == value and value >= minimum and value <= maximum and math.abs(value) < math.huge
end
function Finite.integer(value: any, minimum: number, maximum: number): boolean
    return Finite.number(value, minimum, maximum) and value % 1 == 0
end
function Finite.vector(value: any, maxMagnitude: number): boolean
    if typeof(value) ~= "Vector3" then return false end
    return Finite.number(value.X, -maxMagnitude, maxMagnitude)
        and Finite.number(value.Y, -maxMagnitude, maxMagnitude)
        and Finite.number(value.Z, -maxMagnitude, maxMagnitude)
        and value.Magnitude <= maxMagnitude
end
function Finite.id(value: any, maxBytes: number): boolean
    return type(value) == "string" and #value > 0 and #value <= maxBytes and string.match(value, "^[%w_%-]+$") ~= nil
end
return Finite
