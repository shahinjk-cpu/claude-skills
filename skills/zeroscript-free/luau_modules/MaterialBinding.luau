--!strict
-- Edit-time helper; use only approved, uploaded map IDs. Returns unattached SurfaceAppearance.
local Binding={}
function Binding.create(ids: {[string]: string}): SurfaceAppearance
    local channels={"ColorMap","NormalMap","RoughnessMap","MetalnessMap"}
    for _,key in channels do
        local id=ids[key]
        assert(type(id)=="string" and string.match(id,"^rbxassetid://[1-9]%d*$"),"Missing approved content ID: "..key)
    end
    local surface=Instance.new("SurfaceAppearance");surface.Name="AstroMaterial"
    surface.ColorMap=ids.ColorMap;surface.NormalMap=ids.NormalMap;surface.RoughnessMap=ids.RoughnessMap;surface.MetalnessMap=ids.MetalnessMap
    return surface -- parent to reviewed MeshPart only after checking existing appearance
end
return Binding
