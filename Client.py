
__author__ = 'Alexandr Samoylov'


class Client:
    """
    Клиент
    Содержит информацию о соединении, состоянии и подписке клиента.
    При подключении клиент добавляется с состоянием CS_NEW, и должен отправить список полей данных, которые
    ему необходимы. После этого он переходит в состояние CS_SUBSCRIBED и может получать данные.
    Остановленный клиент переходит в состоянии CS_DEAD, что говорит о том, что клиента можно удалять (?)
    """
    # Client states
    CS_NEW = 0         # "свежие туристы": надо узнать, чего клиент от нас хочет
    CS_SUBSCRIBED = 1  # клиент прислал список полей, можно отправлять ему данные
    CS_DEAD = 2        # пока не будет использоваться

    def __init__(self, connection):
        self.connection = connection  # сокет
        self.state = Client.CS_NEW    # состояние клиента
        self.subscription = []        # данные, на которые клиент подписан

    def set_subscription(self, subscription):
        """
        Устанавливает и обновляет подписку клиента на данные.
        :param subscription: список полей, на которые клиент подписывается.
        :return: нет.
        """
        self.subscription = [].append(subscription)

    def get_subscription(self):
        return self.subscription

    def get_socket(self):
        return self.connection
