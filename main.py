"""
Created on 03 July 2015

@author: Alexandr Samoylov

Аргументы CLI:
-f <float> - интервал отправки данных, больше - лучше, но больше нагрузка
-w <filename> - запись JSON-данных в файл, чтобы использовать с backend_stub.py (после разработки механизма подписок
                backend_stub работать не будет)
"""

# DYNAMIC STATE: what if data is present and can be updated, but
# no clients are present? What if one reconnects?

from sim_state import SimState
import time
from NetSender import NetSender
import sys

# FIXME Статические данные отправляются только первому клиенту и только когда он подключается впервые или строго один.
# TODO Добавить механизм подписки на данные - это сильно снизит трафик

# backend states
STATE_STOP = 0       # бэкенд стоит
STATE_NOCLIENTS = 1  # просто ждём клиентов, опрашивая подключения каждый WAIT_INTERVAL секунд
STATE_NODATA = 2     # ждём статических данных из AC, интервал WAIT_INTERVAL
STATE_DYNAMIC = 3    # можно выдавать динамические данные с интервалом CYCLE_INTERVAL

CYCLE_INTERVAL = 0.1  # интервал обновления динамических данных, можно переопределить ключом -f
WAIT_INTERVAL = 5     # интервал для состояний NOCLIENTS/NODATA

globalState = STATE_STOP  # исходное состояние

if __name__ == '__main__':
    filename = ''
    if len(sys.argv) > 1:
        try:
            w_index = sys.argv.index('-w')
            filename = sys.argv[w_index + 1]
        except ValueError:
            pass
        try:
            f_index = sys.argv.index('-f')
            CYCLE_INTERVAL = float(sys.argv[f_index + 1])
            print("Set send delay to {} sec".format(sys.argv[f_index + 1]))
        except ValueError:
            pass

    print("Starting data capture")
    simState = SimState()
    print("SimState OK")

    # network init
    print("Initializing network")
    net = NetSender()
    if filename != '':
        net.allowWriteToFile(filename)
    net.start()
    print("Networking is running")
    globalState = STATE_NOCLIENTS
    prev_globalState = globalState
    try:
        while globalState != STATE_STOP:
            # Никого нет, возможно, и не было
            if net.clientCount == 0:
                prev_globalState = globalState
                globalState = STATE_NOCLIENTS  # cleanup / remember state / ...?

            if globalState == STATE_NOCLIENTS:
                # Здесь будем проверять, не появился ли клиент
                if net.clientCount > 0:
                    if prev_globalState == STATE_NOCLIENTS:
                        globalState = STATE_NODATA
                    else:
                        globalState = prev_globalState
                else:
                    # Нет, подождём ещё
                    print("No clients, waiting for another " + str(WAIT_INTERVAL) + " seconds.")
                    time.sleep(WAIT_INTERVAL)

            elif globalState == STATE_NODATA:
                # Это состояние должно говорить, что AC не работает. И только это.
                # Клиенты получают пустое сообщение.
                simState.update()
                if simState.get_dynamic_info() is None:
                    print("No static data available, probably Assetto Corsa simulation is not running")
                    net.sendToAll(simState.JSON_EMPTY)
                    time.sleep(WAIT_INTERVAL)
                else:
                    # Статика есть. AC работает и можно с неё брать данные.
                    print("Static data received")
                    net.sendToAll(simState.static_json)
                    globalState = STATE_DYNAMIC  # один цикл динамики пропускаем, не важно, не навредит
                    time.sleep(CYCLE_INTERVAL)

            elif globalState == STATE_DYNAMIC:
                # Достаём и рассылаем данные.
                # TODO Перевод на механизм подписки
                simState.update()
                if simState.get_dynamic_info() is not None:
                    if simState.get_dynamic_info().get("status") == 0:
                        globalState = STATE_NODATA
                        time.sleep(CYCLE_INTERVAL)  # if still nothing, it will wait WAIT_INTERVAL
                    else:
                        net.sendToAll(simState.dynamic_json)
                        time.sleep(CYCLE_INTERVAL)
                else:  # dynamic_json == "" which is the case after the simState cleanup on AC exit
                    globalState = STATE_NODATA
    except (KeyboardInterrupt, SystemExit):
        net.stop()
        net.closeSockets()
        print("Backend was stopped")
