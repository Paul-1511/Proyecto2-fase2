from neo4j import GraphDatabase
import pandas as pd
from sklearn.neighbors import NearestNeighbors

# Conexión con la base de datos Neo4j
class Neo4jConnection:
    
    def __init__(self, uri, user, pwd):
        self.__uri = uri
        self.__user = user
        self.__pwd = pwd
        self.__driver = None
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__pwd))
        except Exception as e:
            print("Failed to create the driver:", e)
        
    def close(self):
        if self.__driver is not None:
            self.__driver.close()
        
    def query(self, query, parameters=None, db=None):
        assert self.__driver is not None, "Driver not initialized!"
        session = None
        response = None
        try: 
            session = self.__driver.session(database=db) if db is not None else self.__driver.session() 
            response = list(session.run(query, parameters))
        except Exception as e:
            print("Query failed:", e)
        finally: 
            if session is not None:
                session.close()
        return response

# Configurar conexión
conn = Neo4jConnection(uri="bolt://localhost:7687", user="neo4j", pwd="tu_contraseña")

# Obtener datos de videojuegos de Neo4j
query = """
MATCH (game:Videojuego)
RETURN game.nombre AS nombre, game.consola AS consola, game.estudio AS estudio, 
       game.categoría AS categoría, game.multijugador AS multijugador, 
       game.duración AS duración, game.precio AS precio
"""
games_df = pd.DataFrame([dict(record) for record in conn.query(query)])

# Convertir datos a formato numérico para k-NN
games_df['multijugador'] = games_df['multijugador'].apply(lambda x: 1 if x else 0)
games_numeric = pd.get_dummies(games_df, columns=['consola', 'estudio', 'categoría'])

# Entrenar el modelo k-NN
knn = NearestNeighbors(n_neighbors=5, algorithm='auto').fit(games_numeric)

# Función para hacer recomendaciones
def recomendar_videojuegos(nombre_juego):
    juego_index = games_df.index[games_df['nombre'] == nombre_juego].tolist()[0]
    distances, indices = knn.kneighbors([games_numeric.iloc[juego_index]])
    nombres_recomendados = games_df.iloc[indices[0]]['nombre'].values
    return nombres_recomendados

# Hacer una recomendación
recomendaciones = recomendar_videojuegos('Nombre del Juego')
print("Juegos recomendados:", recomendaciones)

# Cerrar conexión
conn.close()
