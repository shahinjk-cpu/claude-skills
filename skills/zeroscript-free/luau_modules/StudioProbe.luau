-- Read-only bounded capture of a caller-selected subtree. No source, player data or remote invocation.
-- Run in edit mode for model structure; use the actual client for rendered GUI pixels.
local M = {}
local function v3(v) return {v.X, v.Y, v.Z} end
local function v2(v) return {v.X, v.Y} end
function M.capture(root, limit)
    assert(typeof(root) == "Instance", "explicit instance root required")
    limit = limit or 1000
    assert(type(limit) == "number" and limit % 1 == 0 and limit >= 1 and limit <= 5000, "node budget")
    local queue = {{node = root, parent = 0}}
    local result = {}
    local truncated = false
    local index = 1
    while index <= #queue do
        local item = queue[index]
        local node = item.node
        local row = {id = index, parent = item.parent, name = node.Name, class = node.ClassName}
        if node:IsA("BasePart") then
            row.size = v3(node.Size)
            row.cframe = {node.CFrame:GetComponents()}
            row.anchored = node.Anchored
            row.collide = node.CanCollide
            row.query = node.CanQuery
            row.assemblyRoot = node.AssemblyRootPart and node.AssemblyRootPart:GetFullName() or nil
        elseif node:IsA("GuiObject") then
            row.position = v2(node.AbsolutePosition)
            row.size = v2(node.AbsoluteSize)
            row.visible = node.Visible
            row.clips = node.ClipsDescendants
            row.selectable = node.Selectable
            row.zindex = node.ZIndex
            if node:IsA("TextLabel") or node:IsA("TextButton") or node:IsA("TextBox") then
                row.textFits = node.TextFits
                row.textSize = node.TextSize
                row.textBounds = v2(node.TextBounds)
            end
        elseif node:IsA("ScreenGui") then
            row.enabled = node.Enabled
            row.screenInsets = tostring(node.ScreenInsets)
        elseif node:IsA("Script") then
            row.runContext = tostring(node.RunContext)
            row.enabled = node.Enabled
        elseif node:IsA("LocalScript") then
            row.enabled = node.Enabled
        elseif node:IsA("JointInstance") then
            row.part0 = node.Part0 and node.Part0:GetFullName() or nil
            row.part1 = node.Part1 and node.Part1:GetFullName() or nil
        end
        result[index] = row
        for _, child in ipairs(node:GetChildren()) do
            if #queue >= limit then truncated = true; break end
            table.insert(queue, {node = child, parent = index})
        end
        index = index + 1
    end
    local rs = game:GetService("RunService")
    return {nodes = result, truncated = truncated, running = rs:IsRunning(), client = rs:IsClient(), server = rs:IsServer(), scope = "Observed subtree only; run-local ordinal IDs; names are not persistent identities."}
end
return M
