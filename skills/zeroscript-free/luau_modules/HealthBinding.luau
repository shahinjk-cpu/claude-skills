--!strict
-- Client-side health presenter. Caller owns UI; callback receives ratio, health, max.
local Binding={}
function Binding.attach(player: Player, render: (number,number,number)->())
    local characterConn: RBXScriptConnection?=nil
    local removeConn: RBXScriptConnection?=nil
    local bound: {RBXScriptConnection}={}
    local generation=0
    local function clear()
        generation+=1
        for _,c in bound do c:Disconnect() end
        table.clear(bound)
    end
    local function bind(character: Model)
        clear();local stamp=generation
        task.spawn(function()
            local h=character:FindFirstChildOfClass("Humanoid") or character:WaitForChild("Humanoid",5)
            if stamp~=generation or player.Character~=character or not h or not h:IsA("Humanoid") then return end
            local function update()
                if stamp~=generation then return end
                local maximum=h.MaxHealth
                render(if maximum>0 then math.clamp(h.Health/maximum,0,1) else 0,h.Health,maximum)
            end
            table.insert(bound,h.HealthChanged:Connect(update))
            table.insert(bound,h:GetPropertyChangedSignal("MaxHealth"):Connect(update))
            update()
        end)
    end
    characterConn=player.CharacterAdded:Connect(bind)
    removeConn=player.CharacterRemoving:Connect(function() clear();render(0,0,0) end)
    if player.Character then bind(player.Character) end
    return function()
        clear()
        if characterConn then characterConn:Disconnect() end
        if removeConn then removeConn:Disconnect() end
    end
end
return Binding
