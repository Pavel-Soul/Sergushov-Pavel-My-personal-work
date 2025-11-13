from pymongo import MongoClient

# Класс для работы с MongoDB
class MongoDBManager:
    def __init__(self, db_name):
        # Замените следующие значения на ваши реальные данные
        '''
        username = os.environ["MONGO_USERNAME"]
        password = os.environ["MONGO_PASSWORD"]
        hostname = os.environ["MONGO_HOSTNAME"]
        port = "27017"          # стандартный порт MongoDB

        # Создание строки подключения
        mongo_uri = f"mongodb://{username}:{password}@{hostname}:{port}/"

        # Подключение к MongoDB
        self.client = MongoClient(mongo_uri)
        '''
        self.client = MongoClient('localhost', 27017)
        # self.client = MongoClient('mongodb://localhost:27017/')  # Подключение к MongoDB
        self.db = self.client[db_name]
    # закрытие подключения
    def close(self):
        self.client.close()
    # создание коллекции
    def create_collection(self, collection):
        collection_new = self.db[collection]
    # вставить данные в коллекцию
    def execute_query(self, collection_name, query):
        collection = self.db[collection_name]
        return collection.insert_one(query)
    # удалить данные из коллекции
    def delete_query(self, collection_name, query):
        collection = self.db[collection_name]
        return collection.delete_many(query)
    # обновить одну запись в коллекции
    def update_one_query(self, collection_name, query, update):
        collection = self.db[collection_name]
        return collection.update_one(query, update, upsert=True)
    # обновить все записи в коллекции
    def update_many_query(self, collection_name, query, update):
        collection = self.db[collection_name]
        return collection.update_many(query, update)
    # найти все записи в коллекции
    def fetch_all(self, collection_name, query):
        collection = self.db[collection_name]
        return list(collection.find(query))
    # найти одну запись в коллекции
    def fetch_one(self, collection_name, query):
        collection = self.db[collection_name]
        return collection.find_one(query)