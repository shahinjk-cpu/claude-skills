--!strict
-- Fits an authorized visual-only Model clone to a ViewportFrame. No script execution intended.
local Fit={}
function Fit.mount(frame: ViewportFrame, source: Model, direction: Vector3?, padding: number?)
    local clone=source:Clone()
    assert(clone,"Source must be Archivable")
    for _,inst in clone:GetDescendants() do
        if inst:IsA("LuaSourceContainer") or inst:IsA("Sound") then inst:Destroy() end
    end
    local world=Instance.new("WorldModel");world.Name="AstroPreview";world.Parent=frame;clone.Parent=world
    local camera=Instance.new("Camera");camera.FieldOfView=35;camera.Parent=frame
    local old=frame.CurrentCamera;frame.CurrentCamera=camera
    local cf,size=clone:GetBoundingBox();local center=cf.Position
    local dir=direction or Vector3.new(1,.55,1)
    assert(dir.Magnitude>0 and math.abs(dir.Unit.Y)<.999,"Choose nonvertical view direction")
    local function update()
        local abs=frame.AbsoluteSize
        if abs.X<=0 or abs.Y<=0 then return end
        local halfV=math.rad(camera.FieldOfView)/2
        local halfH=math.atan(math.tan(halfV)*abs.X/abs.Y)
        local radius=math.max(size.Magnitude/2,.01)
        local distance=radius/math.sin(math.min(halfV,halfH))*math.max(1,padding or 1.1)
        camera.CFrame=CFrame.lookAt(center+dir.Unit*distance,center)
    end
    local conn=frame:GetPropertyChangedSignal("AbsoluteSize"):Connect(update);update()
    return function()
        conn:Disconnect()
        if frame.CurrentCamera==camera then frame.CurrentCamera=old end
        world:Destroy();camera:Destroy()
    end
end
return Fit
