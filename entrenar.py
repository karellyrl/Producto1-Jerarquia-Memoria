import pickle
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
from clima import leer_chunks, FEATURES

#Archivo de entrenamiento
archivo = "entrenamiento.csv"
#Prepara la escala de las temperaturas
scaler = StandardScaler()
#Crea el clasificador
modelo = SGDClassifier(loss="log_loss", random_state=0)
#Lee el archivo por partes para no cargarlo completo en RAM
for df in leer_chunks(archivo, 100000, 0):
    df = df.dropna(subset=["precip"] + FEATURES)
    if not df.empty:
        #Calcula la escala por bloques sin cargar todo el archivo
        scaler.partial_fit(df[FEATURES].values)
print("Escala preparada", flush=True)
n = 0
#Lee el archivo por partes para no cargarlo completo en RAM
for df in leer_chunks(archivo, 100000, 0):
    df = df.dropna(subset=["precip"] + FEATURES)
    if not df.empty:
        #Aplica la escala calculada con los datos de entrenamiento
        X = scaler.transform(df[FEATURES].values)
        #Asigna 1 si llovio y 0 si no llovio
        y = (df["precip"] > 0).astype(int).values
        #Actualiza el clasificador con los registros del bloque
        modelo.partial_fit(X, y, classes=[0, 1])
        n += len(y)
        print("Registros entrenados:", n, flush=True)
if n == 0:
    raise ValueError("No hay datos de entrenamiento")
#Guarda el clasificador y la escala para reutilizarlos en las pruebas
with open("modelo.pkl", "wb") as f:
    pickle.dump((scaler, modelo), f)
print("Modelo guardado en modelo.pkl")
