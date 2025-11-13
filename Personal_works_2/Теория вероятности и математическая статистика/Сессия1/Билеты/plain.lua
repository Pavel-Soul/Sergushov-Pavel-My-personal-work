local side, deep = table.unpack(arg)

if not side then
    side = '10'
end

if not deep then
    deep = '10'
end

side = tonumber(side)
deep = tonumber(deep)

function dig_forward(len)
    for i = 1, len do
        while turtle.detect() do
            if not turtle.dig() then
                return false
            end
        end
        turtle.forward()
    end
    return true
end

local started = true
local direct = 0
for slice = 1, deep do
    -- Скапывание одного слоя
    for col = 1, side do
        -- Выкапываем ряд
        if not dig_forward(side - 1) then
            started = false
            break
        end
        -- Если выкопали последнюю колонку, просто разворачиваемся
        if col == side then
            turtle.turnRight()
            if side % 2 == 1 then
                turtle.turnRight()
            end

            -- Поворачиваем в правильном направлении
        elseif direct == 0 then
            turtle.turnRight()
            while turtle.detect() do
                if not turtle.dig() then
                    started = false
                    break
                end
            end
            turtle.forward()
            turtle.turnRight()
        else
            turtle.turnLeft()
            while turtle.detect() do
                if not turtle.dig() then
                    started = false
                    break
                end
            end
            turtle.forward()
            turtle.turnLeft()
        end
        direct = 1 - direct
    end
    direct = 0
    if not started then
        break
    end
    while turtle.detectDown() do
        if not turtle.digDown() then
            started = false
            break
        end
    end
    turtle.down()
end
