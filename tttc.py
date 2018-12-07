from socket import *
import argparse

##########################################################################################
#   playTicTacToe
#   Calling this function will:
#   1.  send a (UDP) request to the server to begin a new game.
#       It will handle the case of lost or dulplicate packets.
#   2.  It will validate user move and sent it to server,
#       and the server will reply with its move and game status.
#       Game state will be rendered at each move and relavent messages will be printed.
#   3.  (2) will repeat until the game ends.
#   The state will be stored as local variables within the function.
#   Please refer to the document for the protocol between client and server.
#######################################################################################
def playTicTacToe(serverName,clientFirst, serverPort=12000):

    clientSocket=socket(AF_INET, SOCK_DGRAM)
    clientSocket.settimeout(1)
    moveNum=0
    cMoves=set()
    sMoves=set()
    lastMoveByClient = None
    gameOver = False
        
    # request
    # This function acts as the interface between client and server.
    # message will be sent to server and it will wait for server's response
    def request(message):
        
        while True:
            try:
                clientSocket.sendto(message.encode(),(serverName,serverPort))
                serverResponse,serverAddress = clientSocket.recvfrom(2048)
            except timeout:
                continue
            return serverResponse.decode()
        
        #The following is mocking server response for testing purpose
        # Comment out code above and uncomment code below to run without a server.
        # mock request start
        '''
        if message == "X":
            return "0 0 0"
        if message == "O":
            return "1 1 0"
        winning_sets=[
            {1,2,3},
            {4,5,6},
            {7,8,9},
            {1,4,7},
            {2,5,8},
            {3,6,9},
            {3,5,7},
            {1,5,9}
        ]
        cWins=any(elem.issubset(cMoves) for elem in winning_sets)
        availableMoves ={1,2,3,4,5,6,7,8,9}-cMoves-sMoves
        move = 0 if len(availableMoves)==0 else availableMoves.pop()
        sWins=any(elem.issubset(sMoves|{move}) for elem in winning_sets)
        status = 1 if cWins else 2 if sWins else 3 if len(availableMoves)==0 else 0
        moveNumber = moveNum if move == 0 else moveNum+1
        return str(moveNumber)+" "+str(move)+" "+str(status)
        '''
        # mock reques end

    #   waitForServerMove
    #   This function will send the last move by client and wait for server's respond.
    #   The message to server will contain move number and client's move, delimited by " "
    #   The server response will contain move number, server's move, and a status number, deliminated by " ".
    #   status codes are [ 0:continue the game, 1:client wins, 2:server wins, 3:draw]
    #   In case of timeout, it will resend the message.
    #   Move number is used to identity duplicate & out-of-order reply
    def waitForServerMove():
        nonlocal moveNum
        nonlocal lastMoveByClient
        # send last client move until server respond with a new state
        message = str(moveNum)+' '+str(lastMoveByClient)

        while True:
            reply = request(message)
            moveNumber, serverMove, status = [int(s) for s in reply.split(" ")]
            if moveNumber == moveNum or moveNumber == moveNum+1:
                # correct move number
                break
            # have to request again if the packet has the wrong move number


        if status == 0:
            # continue the game
            sMoves.add(serverMove)
            moveNum = moveNumber
            render()
            return False
        elif status == 1:
            # game ends on client last move, client wins
            print("You win.")
        elif status == 2:
            # game ends on server last move, server wins
            sMoves.add(serverMove)
            moveNum = moveNumber
            render()
            print("Server wins.")
        elif status == 3:
            #draws
            if moveNumber == moveNum+1:
                # game ends on server last move
                sMoves.add(serverMove)
                moveNum = moveNumber
                render()
            print("Game ends in a draw.")
        nonlocal gameOver
        gameOver=True

    
    #   waitForUserMove
    #   This function prompt user for a valid move,
    #   then render the game state after the move.
    def waitForUserMove():
        nonlocal moveNum
        nonlocal lastMoveByClient
        def validateInput(move):
            try:
                move = int(move)
            except ValueError:
                print("Invalid Input. Must be an integer from 1 to 9.")
                return False
            availableMoves={1,2,3,4,5,6,7,8,9}-cMoves-sMoves
            if move in availableMoves:
                return True
            print("Invalid Input. Available moves are "+str(availableMoves))
            return False

        while True:
            move = input("Please enter your move: ")
            if validateInput(move):
                break
        lastMoveByClient = int(move)
        cMoves.add(int(move))
        moveNum+=1
        render()


    #   render
    #   render function that will print game state 
    def render():
        xPos=cMoves if clientFirst else sMoves
        oPos=sMoves if clientFirst else cMoves
        O="O"
        X="X"
        _=" "
        board=[ _ for i in range(9)]
        for move in xPos:
            board[move-1]=X
        for move in oPos:
            board[move-1]=O
        out = ( ' {6} │ {7} │ {8} \n'
                '───┼───┼───\n'
                ' {3} │ {4} │ {5} \n'
                '───┼───┼───\n'
                ' {0} │ {1} │ {2} \n').format(*board)
        print(out)

    # function that print welcome message
    def welcomeMessage():
        print("################################################################\n")
        print("Welcome to tic tac toe.\nYou can select you move by enter 1 - 9 \n"
            "with the following layout (numpad layout):")
        print(  " 7 │ 8 │ 9 \n"
                "───┼───┼───\n"
                " 4 │ 5 │ 6 \n"
                "───┼───┼───\n"
                " 1 │ 2 │ 3 \n")
        print("################################################################")
        print("{} the first move.".format("You have" if clientFirst else "The server has"))

    # function that request the server to begin a game
    # server will reply with the first move if it goes first
    def initializeGameWithServer():
        #   X: ask server to initialize the game with client first move
        #   O: ask server to initialize the game with server first move
        #   server will reply with "moveNumber move status":
        #       "0 0 0"     if client has the first move
        #       "1 move 0"  if server has the first move, move:[0-9]
        reply = request("X" if clientFirst else "O")
        moveNumber, serverMove, status = [int(s) for s in reply.split(" ")]
        if moveNumber!=0:
            sMoves.add(serverMove)
            moveNum = moveNumber
    #  The function that contain the main execution flow of the game.
    def start():
        initializeGameWithServer()
        welcomeMessage()
        render()
        clientTurn = True
        while not gameOver:
            if clientTurn:
                print("Your Turn.")
                waitForUserMove()
            else:
                print("Waiting for server ...")
                waitForServerMove()
            clientTurn = not clientTurn
        clientSocket.close()
    # Start the game
    start()

     
if __name__ == "__main__":
    # initiate the parser
    parser = argparse.ArgumentParser()  
    parser.add_argument("-s", "--server", required=True, help="Server IP address")
    parser.add_argument("-c", "--clientStart", action="store_true", help="use this if client goes first")
    # read arguments from the command line
    args = parser.parse_args()

    serverIP=args.server
    clientStart=args.clientStart
    playTicTacToe(serverName=serverIP,clientFirst=clientStart)
    