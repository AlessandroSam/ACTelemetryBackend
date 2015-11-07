'''
Created on 27 july 2015

@author: Alexandr Samoylov
'''
import threading
import socket
import select
from Client import Client

MSG_LENGTH = 1024

class NetSender(threading.Thread):
    '''
    Работа с сетью. Отдельный поток собирает и добавляет клиентов; основной занимается получением и рассылкой данных.
    '''
    clients = []  # sockets
    clients_addr = []  # addresses
    clientCount = 0
    lock = threading.Lock()  # реально нужен?
    server_socket = None
    isStopped = False
    writeToFile = False
    outfile = None

    def __init__(self):
        threading.Thread.__init__(self, name='NetSender thread')

    def getClients(self):
        return self.clients

    def addClient(self, client):
        self.lock.acquire()
        self.clients.append(client)
        self.lock.release()

    def allowWriteToFile(self, filename):
        self.outfile = open(filename, "w")
        self.writeToFile = True

    def sendToAll(self, packet):
        """
        МЕТОД БУДЕТ ПЕРЕРАБОТАН
        Отправляет данные клиентам.
        :param packet: отправляемый пакет
        :return: нет
        """
        if self.clientCount == 0:
            # отладочное сообщение
            print("No one wants to get data. This message goes from wrong module and indicates an error in code!")
            return False
        else:
            rd, wr, err = select.select([],
                                        [s.get_socket() for s in self.clients],
                                        [s.get_socket() for s in self.clients])
            for r in wr:
                try:
                    if self.writeToFile:
                        self.outfile.write(packet)
                    r.sendall(packet.encode("UTF-8"))
                    return True
                except (ConnectionResetError, ConnectionAbortedError):
                    i = self.clients.index(r)
                    print("Connection dropped: " + str(self.clients_addr[i]))
                    r.close()
                    self.lock.acquire()
                    self.clients.remove(self.clients[i])
                    self.clients_addr.remove(self.clients_addr[i])
                    self.clientCount -= 1
                    self.lock.release()

            for r in err:
                r.close()
                i = self.clients.index(r)
                self.lock.acquire()
                self.clients.remove(self.clients[i])
                self.clients_addr.remove(self.clients_addr[i])
                self.clientCount -= 1
                self.lock.release()

    def closeSockets(self):
        for s in self.clients:
            s.get_socket().close()
        self.server_socket.close()
        self.clientCount = 0
        if self.writeToFile:
            self.outfile.close()  # ?

    def stop(self):
        self.isStopped = True
        selfconn = socket.socket()
        selfconn.connect(("127.0.0.1", 50000))
        selfconn.close()

    def run(self):
        """
        Основная функция потока. Собираем подключения, добавляем клиентов.
        :return:
        """
        self.server_socket = socket.socket()  # SO_REUSEADDR
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("", 50000))
        self.server_socket.listen(2)
        while not self.isStopped:  # maybe isStopped is useless
            conn, addr = self.server_socket.accept()
            print("Got a connection from " + str(addr))
            conn.setblocking(False)
            client = Client(conn)
            # ждём от клиента его подписки - какие данные, он, собственно, от нас хочет
            subscr_string = ""
            while 1:
                data = str(conn.recv(MSG_LENGTH))
                if data is not None:
                    subscr_string += data
                else:
                    break
            # Формат subscription-строки: названия полей, разделённые через запятую. Названия определены в sim_info.py
            client.set_subscription(subscr_string.split(","))
            self.clients.append(client)
            self.clients_addr.append(addr)
            self.clientCount += 1
