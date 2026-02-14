import mysql.connector
def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Raam@2817",
        database="environment_db"
    ) 
    return connection