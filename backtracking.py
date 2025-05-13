import numpy as np

ACCEPT = "accept"
ABANDON = "abandon"
CONTINUE = "continue"

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
        if not(board[y + 1][x] == -2): # ! ou alors tu peux utiliser un enum (RED = -2) ou alors utiliser la liste de rouges
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

#calculates the time needed to do the route
def calculateTime(route): #route in format route = [(0,0), (1,0, (1,1), ...)]
    
    timeStraight = 2
    timeTurn = 10

    direction = "" # ! Direction de depart non imposée?
    total_time = 0


    if len(route) == 1: #just the start position isnt a route
        return total_time
    
    if len(route) >= 2: #determines the start orientation
        for i in range(1, len(route)):
            #print(f"x change = {route[i][0] - route[i-1][0]}, y change = {route[i][1] - route[i-1][1]}")

            if route[i][0] - route[i-1][0] == 0: #if x coor stays he same then direction is vertial

                if direction == "V" or direction == "": #if going vertical and x doesn't chagne => straight
                    total_time += timeStraight
                else:
                    total_time += timeTurn #else => turn
                direction = "V"

            if route[i][1] - route[i-1][1] == 0:#if the y doesn't change then direction is horizonta

                if direction == "H" or direction == "": #if going vertical and x doesn't chagne => straight
                    total_time += timeStraight
                else:
                    total_time += timeTurn #else => turn
 
                direction = "H" 
            
    return total_time

def examineD1 (greenToCatch: set, partial_solution: list, fastest_time: float):

    greenToCatch = set(greenToCatch)  # maakt een shallow copy
    if partial_solution[-1] in greenToCatch: 
        greenToCatch.remove(partial_solution[-1])
        #print(f"Green to catch got changed to: {greenToCatch}")
    
    partial_sol_time = calculateTime(partial_solution) # ! ne pas calculer la longueur jusqu'a 3 fois par appel
    
    if partial_sol_time > fastest_time: #if the time needed for the route is bigger than the quickest rouyte then abandon 
        return [ABANDON, greenToCatch, fastest_time]
    
    if partial_solution[-1] in partial_solution[:-1]: # ! on ne peut jamais retourner sur le meme chemin?
        return [ABANDON, greenToCatch, fastest_time]
    
    if partial_sol_time <= fastest_time and len(greenToCatch) > 0: #checks if the route is sill ok and if there are still some towers to be caught
        return[CONTINUE, greenToCatch, fastest_time]
    
    if partial_sol_time <= fastest_time and len(greenToCatch) == 0: #sees if the current route is quicker than the quickest and if all the green has been caught
        fastest_time = calculateTime(partial_solution)
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
    solution1 = solveD1(board, getGreen(board), 999999, [startcoordinates], [])[-1] # ! pq ne pas skip putGreen suivi de getGreen?
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
