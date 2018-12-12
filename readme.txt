CMSC 481 Project
UDP Tic Tac Toe
Author: Chen Kuo
ckuo1@umbc.edu

Tic Tac Toe Client Server Program Manual
Do the following steps to run the program.

1. In the terminal, type "python ttts.py" to start the server first.
    The server will use port 12000. If you want to use another port you will have to change it in the code for both tttc.py and ttts.py.

2. After the server has started, you can type in terminal "python tttc.py [-c] [-s serverIP]" to start the client.
    Use -c option if you want the first move.
    You must use -s to specify the IP address of the server.
    You can start multiply clients on different machines as long as the can reach the server's IP.

3. The game can be played on the terminal until it ends.

4. You can interrupt the client or the server with ctrl-c to abort the program. (May need to press 2 times sometimes)

Note:
This program was developed with python 3.7.1 and it has only been tested on Windows 10.
