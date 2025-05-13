# implementation plan:
#* A*: get fastest path between every two "nodes" (starting pos + green pucks)
#* Traveling Salesman Problem: search every possibility (6! = 720) for going through every one of these nodes

import heapq
from itertools import permutations

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

# MARK: A* helpers
def get_last_orientation(path):
	"""
 	get direction at the end of the path
	"""
	if len(path) > 1:
		direction_vector = (path[-1][0] - path[-2][0], path[-1][1] - path[-2][1])
		if direction_vector in DIRS:
			direction = DIRS.index(direction_vector) # positions in DIRS correspond to int values of directions
		else:
			raise Exception("getLastOrientationError: not a valid direction")
	else:
		direction = INIT_DIRECTION
	return direction


def computeLength(path: list, initOrientation: int):
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

def heuristic(a, b):
	"""Manhattan distance for speed"""
	delta_x = abs(a[0] - b[0])
	delta_y = abs(a[1] - b[1])
	return delta_x * timeStraight + delta_y * timeStraight

# MARK: A*
def a_star(start, goal, red_pucks, board_size):
	"""
	A* algorithm with heuristic-prioritized neighbor exploration
	"""
	width, height = board_size

	open_set = []
	heapq.heappush(open_set, (heuristic(start, goal), 0, start, [start]))
	visited = set()

	while open_set:
		est_total_cost, cost_so_far, current, path = heapq.heappop(open_set)

		if current == goal:
			return path

		# you shouldn't go twice on the same point when going from A to B
		if current in visited:
			continue
		visited.add(current)


		# get current direction, could be kept and bubbled around but annoying
		direction = get_last_orientation(path) # if just began, get init direction

		neighbors = []
		for dx, dy in DIRS:
			neighbor = (current[0] + dx, current[1] + dy)
			if (0 <= neighbor[0] < width and
				0 <= neighbor[1] < height and
				neighbor not in red_pucks):
				neighbors.append(neighbor)

		# Sort neighbors by heuristic distance to goal + total cost
		# this will be used as order to search in, to massively speed up the program :)
		neighbors.sort(key=lambda n: (cost_so_far + computeLength([current, n], direction) + heuristic(n, goal)))

		for neighbor in neighbors:
			if neighbor not in visited:
				new_cost = cost_so_far + computeLength([current, neighbor], direction) # computing length twice per neighbor, not optimal...
				estimated_total = new_cost + heuristic(neighbor, goal) # = total heuristic
				heapq.heappush(open_set, (
					estimated_total,
					new_cost,
					neighbor,
					path + [neighbor]
				))

	return None  # No path found

# MARK: TSP
def solve_tsp(start, nodes, red_pucks, board_size):
	"""
	Brute-force TSP for 6 nodes using A*
	"""
	if not input_valid(start, nodes, red_pucks, board_size):
		raise Exception("InputError: Input not valid")

	best_path = None
	best_cost = float('inf')

	for perm in permutations(nodes):
		current_node = start
		full_path = []
		for next_node in perm:
			path = a_star(current_node, next_node, red_pucks, board_size)
			if path is None:
				break
			full_path.extend(path if not full_path else path[1:])
			current_node = next_node
		full_path.extend(a_star(current_node, start, red_pucks, board_size))
		
		cost = computeLength(full_path, initOrientation=INIT_DIRECTION)
		if cost < best_cost:
			best_cost = cost
			best_path = full_path

	return best_path, best_cost


# MARK: HELPER
def input_valid(start: tuple, nodes: set, red_pucks: set, board_size: tuple):
	size_x, size_y = board_size

	# Check board size
	if not (size_x > 0 and size_y > 0):
		return False

	# Check within bounds
	if not (0 <= start[0] < size_x and 0 <= start[1] < size_y):
		return False

	for x, y in nodes:
		if not (0 <= x < size_x and 0 <= y < size_y):
			return False

	for x, y in red_pucks:
		if not (0 <= x < size_x and 0 <= y < size_y):
			return False

	# Ensure no green plug or start is placed on a red plug
	if start in red_pucks or any(node in red_pucks for node in nodes):
		return False

	return True

def print_board(path_go: list, board_size: tuple, green_plugs: set, red_pucks: set):
	for j in range(board_size[1] - 1, -1, -1):
		for i in range(board_size[0]):
			if (i, j) in green_plugs and (i, j) in path_go:
				print("0", end='')
			elif (i, j) in path_go:
				print("-", end='')
			elif (i, j) in red_pucks:
				print("r", end='')
			else:
				print(".", end='')
		print("")


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

# MARK: MAIN
# tsp test
def main():
	green_pucks = set([(0, 5), (2, 5), (2, 4), (2, 2), (3, 3), (3, 1)])

	red_pucks = set([(3, 5), (2, 0), (3, 2), (2, 3)])
	start = (0, 0)

	board_size = (4, 6)
	
	path, cost = solve_tsp(start, green_pucks, red_pucks, board_size)

	print(f"cost: {cost}; path: {path}")
	print_board(path, board_size, green_pucks, red_pucks)
	print(path_to_actions(path, INIT_DIRECTION, green_pucks, False) +[EOS])

""" a* test
def main():
	red_pucks = set([(2,2), (3,2), (0,3), (3, 1), (1, 5)])
	board_size = (8, 10)
	
	start = (0, 0)
	to = (4, 9)
	path_back = a_star(start, to, red_pucks, board_size)
	print_board(set(), path_back, board_size, set(), red_pucks)
"""
main()

# performantietest: tijd: [0, 0, EOS], [0, 0, 1, EOS], [0, 0, 2, EOS], [0, 3, 0, EOS], [0, 1, 0, 2, 0, 0, EOS]
# performantietest: accuraatheid: [0, 0, EOS], []
# performentesten: max snelheid: [0, 2, 0, 1, 0, 4, 0, 4, 2, 0, 4, 1, 0, EOS]