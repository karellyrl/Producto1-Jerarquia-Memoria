import pandas as pd

#Ruta del archivo
archivo = "/home/juan/Descargas/clima_unificado.csv"

#Columnas necesarias
columnas = [
    "clave_estacion",
    "fecha",
    "precipitacion_mm",
    "temp_max_c",
    "temp_min_c",
    "evaporacion_mm",
    "humedad_relativa_pct",
    "presion_barometrica_gcm2"
]

n_train = 0
n_test = 0

#Crea los archivos
with open("entrenamiento.csv", "w") as train:
    with open("prueba.csv", "w") as test:

        #Lee el archivo por partes para no cargarlo completo en RAM
        for i, bloque in enumerate(pd.read_csv(
            archivo,
            usecols=columnas,
            chunksize=100000,
            low_memory=False
        )):
            #Descarta registros que no tienen las variables necesarias
            bloque = bloque.dropna(subset=[
                "precipitacion_mm",
                "temp_max_c",
                "temp_min_c"
            ])

            #Obtiene el año
            fechas = pd.to_datetime(
                bloque["fecha"], errors="coerce"
            )

            anios = fechas.dt.year

            #Selecciona los registros de 2014 a 2017 para entrenar
            entrenamiento = bloque[
                (anios >= 2014) & (anios <= 2017)
            ]

            #Selecciona los registros de 2018 para evaluar el modelo
            prueba = bloque[anios == 2018]

            #Guarda los bloques
            entrenamiento.to_csv(
                train, index=False, header=(i == 0)
            )

            prueba.to_csv(
                test, index=False, header=(i == 0)
            )

            #Cuenta los registros
            n_train += len(entrenamiento)
            n_test += len(prueba)

            if i % 50 == 0:
                print("Bloques revisados:", i + 1, flush=True)

print("Registros de entrenamiento:", n_train)
print("Registros de prueba:", n_test)
