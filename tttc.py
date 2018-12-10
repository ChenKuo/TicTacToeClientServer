import argparse
import socket
import threading
import queue
import sys
import signal

###########################################################################
#   SocketThread
#   All commincation between client and server will go through this class.
#   This is a worker thread class that will receive message on a UDP socket
#   and pass the message to the main thread in a thread-safe way.
#   It will handle the case of timeout/out-of-order/duplicate packets.
###########################################################################
class SocketThread(threading.Thread):
    class Error(Exception):
        pass
    class SocketError(Error):
        pass

    def __init__(self,serverName,serverPort):
        super().__init__()
        self.serverAddress=(serverName, serverPort)
        self.stopper=threading.Event()
        self.messages_received=queue.Queue()
        self.clientSocket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clientSocket.settimeout(1)
        self.uniqueId=0

    # When the thread start it will keep waiting for packets on the socket
    # When it recieves a packet it will put it in a queue so that the main thread can pick it up later
    # Unless the message is "ping", in this case it will reply with "pong" without queueing it
    # It will also throw away message with format not specified by the protocol
    def run(self):
        while not self.stopper.is_set():
            try:
                serverResponse,serverAddress = self.clientSocket.recvfrom(2048)
            except socket.timeout:
                continue
            except Exception as e:
                self.stop()
                break
            serverResponse = serverResponse.decode()
            if serverResponse == 'ping':
                self.send('pong')
            else:
                try:
                    id, move, status = [int(s) for s in serverResponse.split(" ")]
                except:
                    # unknown format, ignore this packet
                    continue
                self.messages_received.put(serverResponse)
        self._close()
    
    # This function will send message to server
    def send(self, message):
        try:
            self.clientSocket.sendto(message.encode(),self.serverAddress)
        except:
            self.stop()

    
    # This function will wait for message from server 
    def receive(self, timeout=None):
        if self.stopper.is_set():
           raise SocketThread.SocketError
        else:
            try:
                message = self.messages_received.get(timeout=timeout)
            except queue.Empty:
                raise TimeoutError
            return message

    # This function will send a message to server, expecting a reply
    # Only reply that correspond to the message will be returned
    def request(self, message):
        # Prepend a unique id to the message before sending it
        # The server will reply with the same id before its reply
        id = self.uniqueId
        self.uniqueId += 1
        message = str(id)+" "+message
        # send and resend message every 0.5 seconds
        # until server reply or it 10 messages has been sent without a reply
        max_num_tries = 10
        num_tries = 0
        self.send(message)
        while num_tries < max_num_tries and not self.stopper.is_set():
            try:
                response = self.receive(0.5)
            except TimeoutError:
                self.send(message)
                num_tries += 1
                continue
            except SocketThread.SocketError:
                break
            else:
                responseId = response.split(" ")[0]
                if responseId != str(id):
                    # wrong packet, get another one
                    continue
                # we have the expected reply
                # remove the unique id before passing it back
                return response[len(responseId)+1:]
        # no more tries
        print("The server is not available at this time.")
        raise SocketThread.SocketError

    # tell the server we are about to close the socket
    # then close the socket without waiting for a response
    def _close(self):
        id = self.uniqueId
        self.uniqueId += 1
        message = str(id)+" close"
        self.send(message)
        self.clientSocket.close()

    # call this function to stop the thread
    # do not call _close() directly
    def stop(self):
        self.stopper.set()
        


##########################################################################################
#   playTicTacToe
#   Calling this function will take the following steps:
#   1.  send a (UDP) request to the server to begin a new game.
#   2.  It will prompt and validate user move and sent it to server,
#       and the server will reply with its move and game status.
#       Game state will be rendered after each move and relavent messages will be printed.
#   3.  (2) will repeat until the server decides game ends.
#   The game state will be stored as local variables
#   Please refer to the document for the communication protocol between client and server.
#######################################################################################
def playTicTacToe(sockListener,clientFirst):
    cMoves=set()
    sMoves=set()

    #   waitForServerMove
    #   This function will send the last move by client and wait for server's respond.
    #   The server response will contain server's move and a status number, deliminated by " ".
    #   status codes are [ 0:in progess, 1:client wins, 2:server wins, 3:tie]
    def waitForServerMove(clientMove):
        try:
            reply = sockListener.request(clientMove)
        except SocketThread.SocketError:
            raise
        else:
            serverMove, status = [int(s) for s in reply.split(" ")]
            IN_PROGRESS, CLIENT_WIN, SERVER_WIN, TIE = 0,1,2,3

            if status == IN_PROGRESS:
                sMoves.add(serverMove)
                render()
                return True

            elif status == CLIENT_WIN:
                print("You win.")

            elif status == SERVER_WIN:
                sMoves.add(serverMove)
                render()
                print("You lose.")

            elif status == TIE:
                if serverMove != 0:
                    # game ends on server last move
                    sMoves.add(serverMove)
                    render()
                print("Game ends in a tie.")

        return False

    
    #   waitForUserMove
    #   This function prompt user for a valid move,
    #   then render the game state after the move.
    def waitForUserMove():

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
            try:
                move = input("Please enter your move: ")
            except:
                raise
                return
            if validateInput(move):
                break

        cMoves.add(int(move))
        render()
        return move


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
        #   server will reply with:
        #       "0 0"     if client has the first move
        #       "move 0"  if server has the first move, move:[0-9]
        print("Inviting the server ...")
        try:
            reply = sockListener.request("X" if clientFirst else "O")
        except SocketThread.SocketError:
            raise
        else:
            serverMove, status = [int(s) for s in reply.split(" ")]
            if serverMove != 0:
                sMoves.add(serverMove)
 
    #  The function that controls the main execution flow of the game.
    def start():
        def endGame():
            sockListener.stop()
            sockListener.join()
            print("Exiting the game ...")

        try:
            initializeGameWithServer()
        except SocketThread.SocketError:
            return endGame()

        welcomeMessage()
        render()
        clientTurn = True
        playerMove=None
        inProgress = True
        while inProgress:
            if clientTurn:
                print("Your Turn.")
                try:
                    playerMove = waitForUserMove()
                except:
                    print("interrupted")
                    return endGame()
            else:
                print("Waiting for server ...")
                try:
                    inProgress = waitForServerMove(playerMove)
                except SocketThread.SocketError:
                    return endGame()

            clientTurn = not clientTurn
        
        print("Thank you for playing the game.")
        return endGame()
    
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

    sock_thread = SocketThread (serverIP, serverPort=12000)
    sock_thread.start()

    
    def signal_handler(sig, frame):
        print("interruption!")
        sock_thread.stop()
        sock_thread.join()
        #sys.exit(0)
    signal.signal(signal.SIGINT,signal_handler)

    playTicTacToe(sockListener=sock_thread,clientFirst=clientStart)
    
    