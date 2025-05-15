import numpy as np

ACCEPT = 0
ABANDON = 1
CONTINUE = 2

# Directions
UP, LEFT, DOWN, RIGHT = 0, 1, 2, 3 # ordered
DIR_PAIRS = [{UP, DOWN}, {LEFT, RIGHT}]
DIRS = [(0, -1), (-1, 0), (0, 1), (1, 0)]  # UP, LEFT, DOWN, RIGHT

#* Parameter
INIT_DIRECTION = UP

# Actions
FORWARDS = 0
LEFT_TURN = 1
RIGHT_TURN = 2
ONE_EIGHTY = 3
PICKUP = 4
EOS = 5

#* Parameters
timeStraight = 2
timeTurn = 5 # turn itself + straight
time180 = 7

# lookup table
action_to_time = { 
	LEFT_TURN: timeTurn,
	RIGHT_TURN: timeTurn,
	ONE_EIGHTY: time180,
	FORWARDS: timeStraight,
	PICKUP: 0,
	EOS: 0
}

#makes the board 
def init_bord(n: int, m:int):
    board = np.zeros((n, m))
    return board

#places all of the green towers
def putGreen(x: int, y: int, board: list):
    if x > -1 and y > -1 and y < len(board) and x < len(board[y]):
        board[y][x] = -1
    return board

#places all of the green towers given a set of coordinates
def putGreenFast(coordinates: set, board: list):
    for i in coordinates:
        x = i[0]
        y = i[1]
        if x > -1 and y > -1 and y < len(board) and x < len(board[y]):
            board[y][x] = -1
    return board

#places all of the red towers
def putRed(x: int, y: int, board: list):
    if x > -1 and y > -1 and y < len(board) and x < len(board[y]):
        print(f"red had been put in {x, y}")
        board[y][x] = -2
    return board

#places all of the red towers given a set of coordinates
def putRedFast(coordinates: set, board: list):
    for i in coordinates:
        x = i[0]
        y = i[1]
        if x > -1 and y > -1 and y < len(board) and x < len(board[y]):
            board[y][x] = -2
    return board

#returns a set of the coordinates of all the green towers on the board
def getGreen(board):
    greenCoordinates = set()
    for i in range(len(board)):
        for j in range(len(board[i])):
            if board[i][j] == -1:
                greenCoordinates.add((j, i))

    return greenCoordinates

#returns a set of the coordinates of all the red towers on the board
def getRed(board):
    redCoordinates = set()
    for i in range(len(board)):
        for j in range(len(board[i])):
            if board[i][j] == -2:
                redCoordinates.add((j, i))

    return redCoordinates   

#given a position fo the board returns a set of coordinates with all of the valid neigbours
def getLegealNeighbour(x: int, y: int, board: list):
    neigbours = set()
    m = len(board)
    n = len(board[0])

    if not( y + 1 > m-1):
        if not(board[y + 1][x] == -2):
            neigbours.add((x, y+1))

    if not(y-1 < 0):
        if not board[y-1][x] == -2:
            neigbours.add((x, y-1))
        
    if not(x + 1 > n-1):
        if not board[y][x + 1] == -2:
            neigbours.add((x+1, y))

    if not (x - 1 < 0 ):
        if not board[y][x-1] == -2:
            neigbours.add((x-1, y))

    return neigbours

def visualise_solution(route:list, board:list):
    steps = 1
    for i in route:
        board[i[1]][i[0]] = steps
        steps += 1

    return board

def path_to_actions(path: list, initOrientation: int, nodes: set, going_back: bool):
	"""
	Converts a path to an action sequence for a vehicle.
	"""
	if len(path) <= 1:
		return []

	orientation = initOrientation
	actions = []

	for i in range(len(path) - 1):
		current = path[i]
		next_pos = path[i + 1]

		x1, y1 = current
		x2, y2 = next_pos

		# Determine movement direction
		if x1 == x2:
			if y1 < y2:
				new_orientation = UP
			else:
				new_orientation = DOWN
		elif y1 == y2:
			if x1 < x2:
				new_orientation = RIGHT
			else:
				new_orientation = LEFT
		else:
			raise Exception("Invalid path: weird movement")

		# Determine turn action
		if new_orientation == orientation:
			pass  # no turn needed
		elif {orientation, new_orientation} in DIR_PAIRS:
			actions.append(ONE_EIGHTY)
		elif new_orientation - orientation == 1 or (orientation == RIGHT and new_orientation == UP):
			actions.append(LEFT_TURN)
		elif new_orientation - orientation == -1 or (orientation == UP and new_orientation == RIGHT):
			actions.append(RIGHT_TURN)
		else:
			print(f"orientation: {orientation}, new_orientation: {new_orientation}")
			raise Exception("Unexpected orientation change.")

		# Move forward
		actions.append(FORWARDS)
		orientation = new_orientation

		# Check if we just arrived at a node (but not the start, neither while going back)
		if next_pos in nodes and not going_back:
			actions.append(PICKUP)

	return actions

def calculateTime(path: list, initOrientation: int):
	"""
	We compute the time cost of some path
	Depends mainly on the amount of turns
	"""

	totalTime = 0

	if len(path) <= 1:
		return totalTime

	actions = path_to_actions(path, initOrientation, set(), True)

	for action in actions:
		totalTime += action_to_time.get(action)

	return totalTime

def examineD1 (greenToCatch: set, partial_solution: list, fastest_time: float):

    greenToCatch = set(greenToCatch)  # maakt een shallow copy
    if partial_solution[-1] in greenToCatch: 
        greenToCatch.remove(partial_solution[-1])
        #print(f"Green to catch got changed to: {greenToCatch}")
    
    partial_sol_time = calculateTime(partial_solution, initOrientation=INIT_DIRECTION)
    
    if partial_sol_time > fastest_time: #if the time needed for the route is bigger than the quickest rouyte then abandon 
        return [ABANDON, greenToCatch, fastest_time]
    
    if partial_solution[-1] in partial_solution[:-1]:
        return [ABANDON, greenToCatch, fastest_time]
    
    if partial_sol_time <= fastest_time and len(greenToCatch) > 0: #checks if the route is sill ok and if there are still some towers to be caught
        return[CONTINUE, greenToCatch, fastest_time]
    
    if partial_sol_time <= fastest_time and len(greenToCatch) == 0: #sees if the current route is quicker than the quickest and if all the green has been caught
        fastest_time = calculateTime(partial_solution, initOrientation=INIT_DIRECTION)
        return [ACCEPT, greenToCatch,fastest_time] 
    

             
def extendD1 (board: list, partial_solution: list):
    extended_partial_solutions = []
    x = partial_solution[len(partial_solution) - 1][0]
    y = partial_solution[len(partial_solution)- 1][1]

    legalNeig = getLegealNeighbour(x, y, board) 

    for i in legalNeig: 
        extended_partial_solutions.append(partial_solution + [i])

    return extended_partial_solutions

def solveD1 (board: list, greenToCatch: list, max_time: float, partial_solution: list, all_solutions: list):

    exam = examineD1 (greenToCatch,partial_solution, max_time) #does the examination for the partial solution
    if exam[0] == ACCEPT: #if the solution is accepted return ok exam = ["Status", green to catch, fastest_time]
        max_time = exam[2]
        all_solutions.append(partial_solution)
    else:
        if exam[0] == CONTINUE: #if the solution could become smthn continue
            extended_partial_solutions = extendD1(board, partial_solution) #gives an array with partial solutions
            for extended in extended_partial_solutions: #for every partial solution
                solveD1(board, exam[1], exam[2], extended, all_solutions) #go again
    
    return all_solutions

def FindPath(board: list, startcoordinates:tuple, finishcoordinates: tuple, visualise: bool):
    solution1 = solveD1(board, getGreen(board), 999999, [startcoordinates], [])[-1]
    solution2 = solveD1(board, [finishcoordinates], 9999999, [solution1[-1]], [])[-1]
    #print(f"solution 1 {solution1} solution 2 {solution2}")

    if visualise:
        pass
        print(visualise_solution(solution1, board))
        print(visualise_solution(solution2, board))

    return solution1 + solution2[1:]




def main():
    board = init_bord(4, 6)
    board = putGreenFast(set([(1, 2), (3, 1), (2, 3)]), board)
    board = putRedFast(set([(2,2), (3,2)]), board)
    print(board)
    print(FindPath(board, (0,0), (0,0), False))




main()
