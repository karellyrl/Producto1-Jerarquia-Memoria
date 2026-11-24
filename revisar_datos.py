import pandas as pd

#Ruta del archivo
archivo = "/home/juan/Descargas/clima_unificado.csv"

#Conteo por año
conteo = {}

#Lee el archivo por partes para no cargarlo completo en RAM
for bloque in pd.read_csv(
    archivo,
    usecols=["fecha", "precipitacion_mm", "temp_max_c", "temp_min_c"],
    chunksize=100000,
    low_memory=False
):
    #Descarta registros que no tienen las variables necesarias
    bloque = bloque.dropna()

    #Cuenta los registros por año
    fechas = pd.to_datetime(bloque["fecha"], errors="coerce")
    anios = fechas.dt.year.value_counts()

    #Suma los registros completos de cada año entre bloques
    for anio, cantidad in anios.items():
        conteo[anio] = conteo.get(anio, 0) + cantidad

#Muestra los resultados
for anio in sorted(conteo):
    print(anio, ":", conteo[anio])

print("Total de registros completos:", sum(conteo.values()))
