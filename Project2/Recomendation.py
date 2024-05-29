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
            print("Driver created successfully")
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
conn = Neo4jConnection(uri="bolt://localhost:7687", user="neo4j", pwd="choperata")

# Verificar si el driver se creó correctamente
if conn._Neo4jConnection__driver is None:
    print("Unable to connect to the database. Please check your credentials and connection settings.")
else:
    # Obtener datos de videojuegos de Neo4j
    query = """
    MATCH (game:Videojuego)
    RETURN game.nombre AS nombre, game.consola AS consola, game.estudio AS estudio, 
           game.categoría AS categoría, game.multijugador AS multijugador, 
           game.duración AS duración, game.precio AS precio
    """
    results = conn.query(query)
    
    if results is None:
        print("No results returned. Please check your query and authentication.")
    else:
        games_df = pd.DataFrame([dict(record) for record in results])

        # Convertir columna 'multijugador' a numérico (0 o 1)
        games_df['multijugador'] = games_df['multijugador'].apply(lambda x: 1 if x else 0)

        # Aplicar One-Hot Encoding a las columnas categóricas 'consola', 'estudio' y 'categoría'
        games_numeric = pd.get_dummies(games_df, columns=['consola', 'estudio', 'categoría'])

        # Excluir la columna 'nombre' de los datos numéricos para el modelo
        games_numeric = games_numeric.drop(columns=['nombre'])
        
        # Entrenar el modelo k-NN
        knn = NearestNeighbors(n_neighbors=5, algorithm='auto').fit(games_numeric)

        # Función para hacer recomendaciones
        def recomendar_videojuegos(filtro=None, valor=None):
            if filtro and valor:
                if filtro == 'precio':
                    juegos_filtrados = games_df[games_df['precio'] <= float(valor)]
                elif filtro == 'categoría':
                    juegos_filtrados = games_df[games_df['categoría'].str.contains(valor, case=False)]
                elif filtro == 'consola':
                    juegos_filtrados = games_df[games_df['consola'].str.contains(valor, case=False)]
                else:
                    print("Filtro no válido.")
                    return []
            else:
                juegos_filtrados = games_df

            if juegos_filtrados.empty:
                print("No se encontraron juegos con los criterios especificados.")
                return []

            juegos_filtrados_numeric = pd.get_dummies(juegos_filtrados, columns=['consola', 'estudio', 'categoría'])
            juegos_filtrados_numeric = juegos_filtrados_numeric.drop(columns=['nombre'])

            n_neighbors = min(5, len(juegos_filtrados_numeric))
            if n_neighbors == 0:
                print("No hay suficientes juegos para recomendar.")
                return []

            knn_filtrado = NearestNeighbors(n_neighbors=n_neighbors, algorithm='auto').fit(juegos_filtrados_numeric)
            
            distances, indices = knn_filtrado.kneighbors(juegos_filtrados_numeric)
            nombres_recomendados = juegos_filtrados.iloc[indices[0]]['nombre'].values
            return nombres_recomendados

        # Menú interactivo
        while True:
            print("\nMenu de Recomendaciones")
            print("1. Recomendaciones por Precio")
            print("2. Recomendaciones por Categoría")
            print("3. Recomendaciones por Consola")
            print("4. Salir")
            choice = input("Selecciona una opción: ")

            if choice == '1':
                max_precio = input("Ingresa el precio máximo: ")
                recomendaciones = recomendar_videojuegos(filtro='precio', valor=max_precio)
                print("Juegos recomendados:", recomendaciones)
            elif choice == '2':
                categoria = input("Ingresa la categoría: ")
                recomendaciones = recomendar_videojuegos(filtro='categoría', valor=categoria)
                print("Juegos recomendados:", recomendaciones)
            elif choice == '3':
                consola = input("Ingresa la consola: ")
                recomendaciones = recomendar_videojuegos(filtro='consola', valor=consola)
                print("Juegos recomendados:", recomendaciones)
            elif choice == '4':
                print("Saliendo...")
                break
            else:
                print("Opción no válida. Inténtalo de nuevo.")

    # Cerrar conexión
    conn.close()
