import pickle
import re
import unicodedata

import warnings
import numpy as np
warnings.filterwarnings("ignore", category=RuntimeWarning)  #Omite avisos numericos
import pandas as pd

#Temperaturas utilizadas como entradas del clasificador
FEATURES = ["tmax", "tmin"]


#Elimina acentos y caracteres para comparar nombres de columnas
def _limpia(nombre):
    n = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", n.lower())


def normalizar_columnas(df):


    #Relaciona los nombres originales con los nombres usados por el programa
    mapa = {}
    for c in df.columns:
        n = _limpia(c)
        if "precip" in n:
            mapa[c] = "precip"
        elif n.startswith("tempmax") or n.startswith("temperaturamax"):
            mapa[c] = "tmax"
        elif n.startswith("tempmin") or n.startswith("temperaturamin"):
            mapa[c] = "tmin"
        elif "evap" in n:
            mapa[c] = "evap"
        elif n.startswith("hum"):
            mapa[c] = "hum"
        elif n.startswith("pres"):
            mapa[c] = "pres"
    #Conserva la precipitacion y las dos temperaturas
    salida = pd.DataFrame(index=df.index)
    for col in ["precip"] + FEATURES:
        origen = [c for c, t in mapa.items() if t == col]
        if origen:
            #Toma el primer valor disponible
            serie = df[origen].apply(pd.to_numeric, errors="coerce").bfill(axis=1).iloc[:, 0]
        else:
            serie = np.nan  #Variable sin datos
        salida[col] = serie
    return salida.astype(float)


def leer_chunks(csv, chunk_rows, max_chunks):

    lector = pd.read_csv(csv, chunksize=chunk_rows, low_memory=False, on_bad_lines="skip")
    for i, trozo in enumerate(lector):
        if max_chunks and i >= max_chunks:
            break
        yield normalizar_columnas(trozo)


#Convierte el bloque a bytes para poder guardarlo
def serializar(df):
    return pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL)


#Convierte los bytes nuevamente en una tabla
def deserializar(b):
    return pickle.loads(b)


#Clasifica los registros
class Clasificador:
    def __init__(self, ruta="modelo.pkl"):
        #Recupera el modelo entrenado y la escala de las temperaturas
        with open(ruta, "rb") as f:
            self.scaler, self.modelo = pickle.load(f)
        self.filas = self.aciertos = self.lluvia = 0

    def procesar(self, df):
        #Descarta registros que no tienen las variables necesarias
        df = df.dropna(subset=["precip"] + FEATURES)
        if df.empty:
            return
        #Considera lluvia cuando la precipitacion es mayor que cero
        y = (df["precip"] > 0).astype(int).values
        #Aplica la escala calculada con los datos de entrenamiento
        X = self.scaler.transform(df[FEATURES].values)
        #Compara las predicciones con las etiquetas reales
        self.aciertos += int((self.modelo.predict(X) == y).sum())
        self.filas += len(y)
        self.lluvia += int(y.sum())

    #Calcula el porcentaje de lluvia y la exactitud del modelo
    def resumen(self):
        return {"filas": self.filas, "pct_lluvia": round(100*self.lluvia/max(1,self.filas),2),
                "accuracy": round(self.aciertos/self.filas,4) if self.filas else None}
