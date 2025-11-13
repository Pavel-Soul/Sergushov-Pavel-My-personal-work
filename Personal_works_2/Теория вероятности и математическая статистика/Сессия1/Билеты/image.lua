local file = arg[1]


local f = io.open(file, 'r')
local mon = peripheral.wrap(arg[2] or "right")

mon.clear()
mon.setCursorPos(1, 1)

count = 0
while true do
    local line = f:read()
    if not line then
        break
    end
    count = count + 1
    mon.setCursorPos(1, count)
    mon.blit(string.rep(" ", string.len(line)), line, line)
end
