--!strict
-- Read-only Motor6D/Bone inventory. Duplicate names are flagged, not silently overwritten.
local RigMap={}
function RigMap.inspect(rig: Model)
    local joints={};local names: {[string]: number}={}
    for _,item in rig:GetDescendants() do
        if item:IsA("Motor6D") then
            table.insert(joints,{name=item.Name,path=item:GetFullName(),part0=if item.Part0 then item.Part0.Name else nil,part1=if item.Part1 then item.Part1.Name else nil,c0=item.C0,c1=item.C1})
            names[item.Name]=(names[item.Name] or 0)+1
        elseif item:IsA("Bone") then
            table.insert(joints,{name=item.Name,path=item:GetFullName(),parent=if item.Parent then item.Parent.Name else nil,rest=item.CFrame})
            names[item.Name]=(names[item.Name] or 0)+1
        end
    end
    local duplicates={}
    for name,count in names do if count>1 then table.insert(duplicates,name) end end
    table.sort(duplicates)
    return joints,duplicates
end
return RigMap
