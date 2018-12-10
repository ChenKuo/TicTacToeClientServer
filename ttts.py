import socket
import threading
import sys
import signal
import time
import queue
import random

##################################################################
# socketReceiver 
# This is a thread class that will receive datagram on the socket
# and spawn a client replier thread if the game request is valid.
# Other type of messages will be ignored if the client has not requested a game.
# If a replier thread already exist for the client then 
# the message will be passed to the client replier thread
###################################################################
class socketReceiver(threading.Thread):
    def __init__(self, socket):
        super().__init__()
        self.socket=socket
        self.threads={}
        self.lock=threading.Lock()
        self.stopper = threading.Event()
    
    def run(self):
        print('the server is ready to receive')
        while not self.stopper.is_set():
            try:
                message, clientAddress = self.socket.recvfrom(2048)
            except socket.timeout:
                continue
            except ConnectionError as e:
                continue
            except:
                self.stop()
            
            message = message.decode()

            # only create a worker thread if the client requests a new game
            if message in ("0 X","0 O"):
                if clientAddress not in self.threads:
                    thread = ClientReplier(self.socket,clientAddress,message)        
                    self.threads[clientAddress] = thread
                    thread.start()
                
                elif not self.threads[clientAddress].is_alive():
                    self.threads[clientAddress].join()
                    thread = ClientReplier(self.socket,clientAddress,message)
                    self.threads[clientAddress]=thread
                    thread.start()
                else:
                    # thread is already running
                    self.threads[clientAddress].put(message)
                continue

            # if the server has not already open a game with the client, ignore the client
            try:
                thread = self.threads[clientAddress]
            except KeyError:
                # the client has not started a game
                # ignore it
                continue
            else:
                if thread.is_alive():
                    thread.put(message)

        for k in self.threads:
            self.threads[k].stop()
        print("closing socket ...")
        self.socket.close()

    def stop(self):
        self.stopper.set()
    
    def removeDeadThreads(self):
        dead_thread_keys = [k for k in self.threads if not self.threads[k].is_alive()]
        with self.lock:
            for k in dead_thread_keys:
                t = self.threads.pop(k)
                t.join()

###############################################################################
# ClientReplier
# This class is a thread that receive message for a particular client.
# Messages that does not match the protocol will be ignored
# Timeout/duplicate/out-of-order packets are handled
# A spawned client replier thread will be stopped if the client is unresponsive
################################################################################
class ClientReplier(threading.Thread):
    def __init__(self, socket, clientAddress,first_request):
        super().__init__()
        self.socket=socket
        self.clientAddress=clientAddress
        self.queue=queue.Queue()
        self.stopper=threading.Event()
        self.first_request=first_request
    
    def put(self,message):
        self.queue.put(message)
    
    def send(self, message):
        self.socket.sendto(message.encode(), self.clientAddress)


    def run(self):
        print(str(self.clientAddress)+" has started a game.")
        MAX_NUMBER_OF_PING = 5
        numPings=0
        IN_PROGRESS, CLIENT_WIN, SERVER_WIN, TIE = '0','1','2','3'
        id, clientSymbol = self.first_request.split(" ")
        id = int(id)
        move = 0 if clientSymbol == "X" else random.choice((1,2,3,4,5,6,7,8,9))
        status = IN_PROGRESS
        last_reply = str(id)+" "+str(move)+" "+status
        # the game state :
        cMoves = set()
        sMoves = {move}
 
        self.send(last_reply)
        while not self.stopper.is_set():
            try:
                message = self.queue.get(timeout=1)
            except queue.Empty:
                # timed out
                if numPings <= MAX_NUMBER_OF_PING:
                    self.send("ping")
                    numPings += 1
                else:
                    print(str(self.clientAddress)+" is not responsive.")
                    self.stop()
                continue
            numPings = 0

            try:
                message_id = int(message.split(" ")[0])
            except ValueError:
                # message with no header id = invalid message
                continue
            else:
                if message_id-id == 0:
                    # duplicate request
                    self.send(last_reply)
                    continue
                elif message_id-id != 1:
                    # filter expired messages
                    continue
            # we have a new message
            
            if message.split(" ")[1] == "close":
                self.stop()
                break
            id = message_id
            try:
                clientMove = int(message.split(" ")[1])
            except (ValueError, IndexError):
                # message has incorret format
                continue
            # game logic
            cMoves|={clientMove}
            winning_sets=[
                {1,2,3}, {4,5,6}, {7,8,9}, {1,4,7},
                {2,5,8}, {3,6,9}, {3,5,7}, {1,5,9} ]
            cWins=any(elem.issubset(cMoves) for elem in winning_sets)
            availableMoves ={1,2,3,4,5,6,7,8,9}-cMoves-sMoves
            # client has won or no more move is available
            if cWins or len(availableMoves) == 0:
                move=0
                status = CLIENT_WIN if cWins else TIE
                last_reply = str(id)+" "+str(move)+" "+status
                self.send(last_reply)
            else:
                # server makes a move
                move = random.sample(availableMoves,1)[0]
                availableMoves-={move}
                sMoves|={move}
                sWins=any(elem.issubset(sMoves) for elem in winning_sets)
            status = CLIENT_WIN if cWins else SERVER_WIN if sWins else TIE if len(availableMoves)==0 else IN_PROGRESS
            
            last_reply = str(id)+" "+str(move)+" "+status
            self.send(last_reply)   
            # while loop ends
        print(str(self.clientAddress)+" exits the game.")

    def stop(self):
        self.stopper.set()



if __name__ == "__main__":
    serverPort = 12000
    serverSocket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSocket.bind(('',serverPort))
    serverSocket.settimeout(1)

    thread_receiver = socketReceiver(serverSocket)
    thread_receiver.start()

    def cleanup():
        thread_receiver.stop()
        thread_receiver.join()
    
    def signal_handler(sig, frame):
        print("A keyboard interruption has occured!")
        cleanup()
        #sys.exit(0)
        
    signal.signal(signal.SIGINT,signal_handler)
    
    while thread_receiver.is_alive():
        thread_receiver.removeDeadThreads()
        sys.stdout.write("#active games = %d \r" % (len(thread_receiver.threads)))
        sys.stdout.flush()
        time.sleep(1)



   

