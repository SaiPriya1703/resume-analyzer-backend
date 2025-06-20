from pymongo import MongoClient

MONGO_URI = "mongodb+srv://saipriyapatancheru:TcRzm6HlnOqUWzQJ@cluster0.0lewkje.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["resume_analyzer"]
users_collection = db["users"]
