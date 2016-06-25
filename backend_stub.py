'''
Created on 02 September 2015
Заменяет игру при тестировании Android-фронтенда.
Использование: python backend_stub.py filename
Несколько файлов data*.txt уже есть в репозитории
@author Alexandr Samoylov
'''
from NetSender import NetSender
import time
import sys

UPDATE_CYCLE_TIME = 0.1

def waitForClient(net, waitTime):
    while net.clientCount == 0:
        print("Waiting for client to connect")
        time.sleep(waitTime)    

if __name__ == '__main__':
    print(sys.argv)
    filename = sys.argv[1]
    if filename == '':
        print("No input file specified.")
    else:
        print("Using file " + filename)
        infile = open(filename, 'r')
        net = NetSender()
        net.start()
        print("NetSender has started")
        for line in infile:
            waitForClient(net, 5)
            net.sendToAll(line)
            time.sleep(UPDATE_CYCLE_TIME)
        print("*****  End of file  *****")
        net.stop()
        net.closeSockets()
        
