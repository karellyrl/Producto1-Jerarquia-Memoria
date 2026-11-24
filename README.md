# Producto 1 – Jerarquía de memoria aplicada a datos meteorológicos

Aplicación en Python que lee registros meteorológicos por bloques y los clasifica como lluvia o sin lluvia. Se compara el intercambio de datos mediante disco, memoria compartida local y memoria remota con KAX. El productor y el consumidor se ejecutan en procesos separados y utilizan un buffer limitado por un semáforo.

## Archivos de datos

Los archivos utilizados en el proyecto se encuentran disponibles en Google Drive debido a su tamaño.

- [Datos originales (8 GB)] https://drive.google.com/file/d/11Zl8Jzu1_TiTPp3sIOY1ICr-4Y1m_4oR/view?usp=drive_link
- [Datos de entrenamiento (2014-2017)] https://drive.google.com/file/d/1UIRh5_TziuulEJDDLUpG6mYsSRubvbZK/view?usp=drive_link
- [Datos de prueba (2018)] https://drive.google.com/file/d/1qnNtmLJeqrVT7wpFFKYSQZSDN6NAR1c9/view?usp=drive_link

## Instalación

En Linux/Ubuntu, con Python 3.10 o compatible:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Preparación de datos y entrenamiento

Se utiliza `clima_unificado.csv`, de aproximadamente 8 GB. Ajustar su ruta en `revisar_datos.py` y `preparar_datos.py`. Los datos originales y los CSV generados no se incluyen en el repositorio por su tamaño.

```bash
python revisar_datos.py
python preparar_datos.py
python entrenar.py
```

Se seleccionaron registros completos de precipitación y temperaturas: 4,554,974 registros de 2014–2017 para entrenamiento y 987,642 de 2018 para prueba. El modelo SGDClassifier utiliza temperatura máxima y mínima; la precipitación se usa únicamente como etiqueta real (mayor que cero = lluvia). El entrenamiento genera `modelo.pkl`. Durante los experimentos el modelo no se modifica.

## Ejecución de las pruebas

```bash
python main.py secuencial --csv prueba.csv --chunk-rows 1000 --max-chunks 0
for medio in disco ram nube; do
    python main.py run --medio "$medio" --slots 2 --chunk-rows 1000 --max-chunks 0 --csv prueba.csv --slot-mb 2
done
```

Para nube se requiere acceso al servidor KAX. Los puertos se pueden configurar con las variables `KAX_REGISTRY_PORT`, `KAX_STORAGE_PORT` y `KAX_BROKER_PORT`; el host con `KAX_HOST`. Los segmentos se reutilizan y se eliminan al terminar.

### Buffering

```bash
for medio in disco ram nube; do
    for retrasos in "0 0.1" "0.1 0" "0.1 0.1"; do
        read -r prod cons <<< "$retrasos"
        python main.py run --medio "$medio" --slots 2 --chunk-rows 1000 --max-chunks 0 --csv prueba.csv --slot-mb 2 --prod-delay "$prod" --cons-delay "$cons"
    done
done
for slots in 1 4; do
    python main.py run --medio ram --slots "$slots" --chunk-rows 1000 --max-chunks 0 --csv prueba.csv --slot-mb 2 --prod-delay 0 --cons-delay 0.1
done
```

`--slots` indica la cantidad de espacios del buffer; `--chunk-rows`, los registros por bloque; `--max-chunks 0`, todo el archivo; `--slot-mb`, el tamaño de cada segmento KAX en MiB; y los retrasos, las pausas adicionales en segundos por bloque.

## Resultados

Cada ejecución agrega una fila a `resultados_nuevos.csv`. Se registran el tiempo total, escritura y lectura, procesamiento, espera del productor y consumidor, ocupación máxima, volumen de datos enviados y memoria reservada. Los tiempos de lectura y escritura pueden solaparse. El volumen enviado corresponde al contenido serializado (codificado en Base64 para KAX), no al tráfico total de red. La memoria reservada no representa toda la RAM del proceso.

| Medio | Tiempo sin retrasos (s) |
|---|---:|
| Secuencial | 7.011 |
| Disco | 38.262 |
| RAM | 13.995 |
| Nube | 83.423 |

Las pruebas finales procesaron 987,642 registros con una exactitud de 73.95 %. El porcentaje real de lluvia fue 24.28 %. El modelo es una clasificación de referencia, no un pronóstico, la exactitud no supera la referencia de predecir siempre sin lluvia (75.72 %).

## Archivos

- `main.py`: procesos, buffer y mediciones.
- `medios.py`: acceso a disco, RAM y nube.
- `clima.py`: lectura, serialización y clasificación.
- `revisar_datos.py`: conteo de registros completos por año.
- `preparar_datos.py`: separación de datos.
- `entrenar.py`: entrenamiento y guardado del modelo.
- `requirements.txt`: dependencias.
- `prompts.md`: registro del apoyo de IA.
