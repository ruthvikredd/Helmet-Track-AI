import mysql.connector

def get_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Gruthvik1234@",
            database="helmettrack"
        )
        return conn
    except mysql.connector.Error as err:
        print("Database Error:", err)
        return None
