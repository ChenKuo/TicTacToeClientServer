import socket
import threading
import sys
import signal
import time
import queue
import random


class socketReceiver(threading.Thread):
    def __init__(self, socket, threads, lock, stopper):
        super().__init__()
        self.socket=socket
        self.threads=threads
        self.lock=lock
        self.stopper = stopper
    
    def run(self):
        print('the server is ready to receive')
        while not self.stopper.is_set():

            message, clientAddress = self.socket.recvfrom(2048)
            with self.lock:
                try:
                    thread = threads[clientAddress]
                except KeyError:
                    thread = socketReplier(self.socket,clientAddress,self.stopper)
                    threads[clientAddress] = thread
                if not thread.is_alive():
                    thread.start()
                thread.forward(message)

    def stop(self):
        self.stopper.set()

class socketReplier(threading.Thread):
    def __init__(self, socket, clientAddress,stopper):
        super().__init__()
        self.socket=socket
        self.clientAddress=clientAddress
        self.queue=queue.Queue()
        self.stopper=stopper
    
    def forward(self,message):
        self.queue.put(message)

    def run(self):
        moveNum, lastMove, lastStatus, cMoves, sMoves = 0, 0, 0, set(), set()

        while not self.stopper.is_set():
            message = self.queue.get().decode()

            if message == "X":
                replyMessage= "0 0 0"
                self.socket.sendto(replyMessage.encode(), self.clientAddress)
                continue
            elif message == "O":
                if moveNum == 1:
                    replyMessage= "1 "+str(move)+" 0"
                    self.socket.sendto(replyMessage.encode(), self.clientAddress)
                    continue
                move = random.choice((1,2,3,4,5,6,7,8,9))
                moveNum, lastMove, lastStatus = 1, move, 0
                sMoves|={move}
                replyMessage= "1 "+str(move)+" 0"
                self.socket.sendto(replyMessage.encode(), self.clientAddress)
                continue

            client_moveNumber, clientMove = [int(s) for s in message.split(" ")]
            print(moveNum, lastMove, lastStatus, cMoves, sMoves)
            if client_moveNumber < moveNum-1:
                continue
            elif client_moveNumber == moveNum-1:
                replyMessage = str(moveNum)+" "+str(lastMove)+" "+str(lastStatus)
                self.socket.sendto(replyMessage.encode(), self.clientAddress)
                continue
        
            moveNum+=1
            cMoves|={clientMove}
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
            if len(availableMoves)==0 or cWins:
                move=0
                sWin=False
            else:
                move = random.sample(availableMoves,1)[0]
                availableMoves-={move}
                sMoves|={move}
                sWins=any(elem.issubset(sMoves) for elem in winning_sets)
            status = 1 if cWins else 2 if sWins else 3 if len(availableMoves)==0 else 0
            moveNum = client_moveNumber+1
            replyMessage = str(moveNum)+" "+str(move)+" "+str(status)
            self.socket.sendto(replyMessage.encode(), self.clientAddress)
            lastMove, lastStatus = move,status       

    def stop(self):
        self.stopper.set()



if __name__ == "__main__":
    serverPort = 12000
    serverSocket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSocket.bind(('',serverPort))

    stopper = threading.Event()
    threads = {}
    lock = threading.Lock()
    thread_receiver = socketReceiver(serverSocket, threads, lock, stopper)

    def signal_handler(sig, frame):
        print("interruption!")
        thread_receiver.stop()
        thread_receiver.join()
        serverSocket.close()
        with lock:
            for k in threads:
                threads[k].join()
        sys.exit(0)
    signal.signal(signal.SIGINT,signal_handler)

    thread_receiver.start()

    
    while True:
        print(threads)
        del_list = []
        with lock:
            for k in threads:
                if not threads[k].is_alive():
                    del_list.append(k)
            for k in del_list:
                del threads[k]
        time.sleep(1)
   


   

