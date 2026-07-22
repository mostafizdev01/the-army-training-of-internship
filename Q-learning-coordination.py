import os

grid = [
        ["🟧","🟧","🟧","🟧","🟧"],
        ["🟧","🟧","🟧","🟧","🟧"],
        ["🟧","🟧","🟧","🟧","🟧"],
        ["🟧","🟧","🟧","🟧","🟧"],
        ["🟧","🟧","🟧","🟧","🟧"]
    ]

robot_row = 0
robot_col = 0

goal_row = 4
goal_col = 4

grid[robot_row][robot_col] = "🤖"

grid[goal_row][goal_col] = "🏠"

# while loop for right direction
while robot_row != goal_row or robot_col != goal_col:

    os.system("cls") # clear screen
# Grid print
    for row in grid:
        for value in row:
           print(value, end=" ")
        print()

    move = input("\nEnter direction (up/down/left/right): ").lower()
    # direction handle with user prompt
    
    grid[robot_row][robot_col] = "🟧"

    if move == "left":
        if robot_col > 0:
           robot_col -= 1

    elif move == "right":
        if robot_col < 4:
            robot_col += 1

    elif move == "up":
        if robot_row > 0:
            robot_row -= 1

    elif move == "down":
        if robot_row < 4:
            robot_row += 1

    else:
        print("Invalid Direction ❌")
    
    grid[robot_row][robot_col] = '🤖'
    
    grid[goal_row][goal_col] = "🏠"

# print after right goals
os.system("cls") # clear screen
print("\n🎉 Goal Reached!")

# robot new position add
grid[robot_row][robot_col] = '🏠'


for row in grid:
    for value in row:
        print(value, end=" ")
    print()
 