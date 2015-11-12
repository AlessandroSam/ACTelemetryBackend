'''
Created on 27 july 2015

@author: Alexandr Samoylov
'''
import threading
import socket
import select
import sim_state
import json
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
        """
        Добавляет клиента в список.
        :param client: добавляемый клент
        :return: нет. Изменяется список self.clients.
        """
        self.lock.acquire()
        self.clients.append(client)
        self.lock.release()

    def allowWriteToFile(self, filename):
        """
        Разрешает запись отправляемых данных в файл для целей отладки и тестирования.
        :param filename: имя файла (ключ командной строки -w)
        :return: нет.
        """
        self.outfile = open(filename, "w")
        self.writeToFile = True

    def removeClientBySocket(self, socket):
        """
        Удаляет клиента, имеющего указанный сокет. Необходимость метода обусловлена тем, что select.select
        возвращает сокет, но в результате мы не знаем точно, с каким клиентом данный сокет ассоциирован.
        :param socket: искомый сокет
        :return: нет. Клиент удаляется из списка self.clients, сокет закрывается.
        """
        for client in self.clients:
            if client.get_socket() == socket:
                socket.close()
                self.clients.remove(client)
                self.clientCount -= 1

    @staticmethod
    def generate_packet(data_dict, subscription):
        """
        Создаёт JSON-пакет с данными для клиента. В случае с динамическими данными из словаря dict берутся только те
        поля, которые указаны в списке subsciption, в остальных случаях при формировании пакета используется словарь
        целиком.
        :param data_dict: словарь с данными (полными) для отправки
        :param subscription: список полей, которые требуется включить в пакет.
        :return: JSON-пакет, готовый к отправке клиенту.
        """
        type = data_dict.get(sim_state.MSG_TYPE_STRING)
        if type == sim_state.MSG_TYPE_STATIC or type == sim_state.MSG_TYPE_EMPTY:
            return json.dumps(data_dict) + "\n"
        else:
            if type == sim_state.MSG_TYPE_DYNAMIC:
                outdict = {}
                for item in subscription:
                    try:
                        outdict.update({item: data_dict.get(item)})
                    except ValueError:
                        print("Cannot retrieve field {} from dynamic data dictionary.", item)
                return json.dumps(outdict) + "\n"
            else:
                print("Unknown data package type: " + type)

    def sendToAll(self, data):
        """
        Отправляет данные клиентам в соответствии с их подпиской. Если клиент не готов принимать данные, пакет будет
        отброшен.
        :param data: словарь с полными данными, из которого выбираются данные для отправки
        :return: нет
        """
        for client in self.clients:  # для каждого клиента в списке
            _, wr, err = select.select([],  # проверяется, готов ли он принимать данные
                                       [client.get_socket()],
                                       [client.get_socket()])
            if len(wr) > 0:  # и если да,
                try:
                    packet = self.generate_packet(data, client.get_subscription())  # формируем JSON-пакет
                    if self.writeToFile:  # если нужно, записываем его в файл
                        self.outfile.write(packet)
                    wr[0].sendall(packet.encode("UTF-8"))  # и отправляемм
                except (ConnectionResetError, ConnectionAbortedError):
                    print("Connection dropped " + str(wr[0].getsockname()))  # потеря соединения с клиентом
                    self.removeClientBySocket(wr[0])  # TODO больше нет необходимости в поиске клиента по его сокету
            if len(err) > 0:
                print("Socket error " + err[0].getsockname())
                self.removeClientBySocket(err[0])

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
        self.server_socket.setblocking(False)
        while not self.isStopped:  # maybe isStopped is useless
            ready = select.select([self.server_socket], [], [], 1)
            if ready[0]:
                conn, addr = self.server_socket.accept()
                print("Got a connection from " + str(addr))
                client = Client(conn)
                conn.setblocking(False)
                # ждём от клиента его подписки - какие данные, он, собственно, от нас хочет
                subscr_string = ""
                while subscr_string.find('.') == -1:
                    ready = select.select([conn], [], [], 3)
                    if ready[0]:
                        # Принимаем данные
                        bytes = conn.recv(MSG_LENGTH)
                        if len(bytes) > 0:
                            data = str(bytes)
                            subscr_string += data
                        else:
                            print("Zero-byte message received. Connection is broken")
                            conn.close()
                            break
                    else:
                        # Клиент не подписался на данные за время тайм-аута. Принудительно отключаем.
                        print("Client couldn't subscribe to data in given time. Closing the connection")
                        conn.close()
                        break
                # Формат subscription-строки: названия полей, разделённые через запятую, конец - точка.
                # Первое поле получает замусоренное имя
                subscr_string = subscr_string[2:len(subscr_string)-1]
                # Названия определены в sim_info.py
                client.set_subscription(subscr_string.split(","))
                print("Subscription:" + str(client.get_subscription()))
                self.clients.append(client)
                self.clients_addr.append(addr)
                self.clientCount += 1


'''
    def sendToAll(self, packet): deprecated
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
            _, wr, err = select.select([],
                                       [s.get_socket() for s in self.clients],
                                       [s.get_socket() for s in self.clients])
            for r in wr:
                try:
                    if self.writeToFile:
                        self.outfile.write(packet)
                    r.sendall(packet.encode("UTF-8"))
                    return True  # возврат после первого же клиента???
                except (ConnectionResetError, ConnectionAbortedError):
                    print("Connection dropped " + str(r.getsockname()))
                    self.removeClientBySocket(r)
            for r in err:
                self.removeClientBySocket(r)
'''