--!strict
-- CanvasGroup visual transition with stale completion protection. Caller manages input/focus.
local TweenService=game:GetService("TweenService")
local Modal={}
function Modal.new(group: CanvasGroup)
    local tween: Tween?=nil
    local complete: RBXScriptConnection?=nil
    local gen=0
    local function cancel()
        gen+=1
        if complete then complete:Disconnect();complete=nil end
        if tween then tween:Cancel();tween:Destroy();tween=nil end
    end
    local api={}
    function api.set(open: boolean,seconds: number,reducedMotion: boolean,onSettled: ((boolean)->())?)
        cancel();local stamp=gen
        local target=if open then 0 else 1
        if open then group.Visible=true end
        if reducedMotion or seconds<=0 then
            group.GroupTransparency=target;group.Visible=open
            if onSettled then onSettled(open) end
            return
        end
        local t=TweenService:Create(group,TweenInfo.new(seconds,Enum.EasingStyle.Quad,Enum.EasingDirection.Out),{GroupTransparency=target})
        tween=t
        complete=t.Completed:Connect(function(state)
            if stamp~=gen or state~=Enum.PlaybackState.Completed then return end
            group.Visible=open
            if complete then complete:Disconnect();complete=nil end
            tween=nil;t:Destroy()
            if onSettled then onSettled(open) end
        end)
        t:Play()
    end
    function api.destroy() cancel() end
    return api
end
return Modal
