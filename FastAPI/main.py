import sqlalchemy
import pyodbc

class MyClass:
    def __init__(self):
        self.connection_string = "******dsnname?driver=ODBC+Driver+17+for+SQL+Server"

******dsnname?driver=ODBC+Driver+17+for+SQL+Server

SQLAlchemy
pyodbc 

create a natural user

I need path parameters with @app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
