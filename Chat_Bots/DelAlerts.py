from pymongo import MongoClient
import os
# '''
username = os.environ["MONGO_USERNAME"]
password = os.environ["MONGO_PASSWORD"]
hostname = os.environ["MONGO_HOSTNAME"]
port = "27017"  # стандартный порт MongoDB, измените при необходимости

# Создание строки подключения
mongo_uri = f"mongodb://{username}:{password}@{hostname}:{port}/"

# Подключение к MongoDB
client = MongoClient(mongo_uri)
# '''
# client = MongoClient('localhost', 27017)

# Создание или выбор базы данных. База данных создается автоматически, если не существует.
db_roBod = client['EmergAlert']

# --------------------- BookRooms ------------------------

db_roBod['Alerts'].delete_many({})
