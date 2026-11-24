# Registro de uso de inteligencia artificial

Herramientas utilizadas: Claude (Anthropic) y ChatGPT (OpenAI).

## Claude — diseño y desarrollo inicial

1. Tengo un archivo CSV de datos meteorológicos de aproximadamente 8 GB. Necesito una aplicación en Python que lo lea por bloques y clasifique los registros como lluvia o sin lluvia, sin cargar todo el archivo en RAM. ¿Cómo puedo organizar el código y separar la lectura, el procesamiento y los medios de almacenamiento?

2. Ayúdame a implementar un productor y un consumidor en procesos separados. El productor debe enviar bloques por disco, memoria compartida local con KAX o memoria remota con KAX. Quiero poder seleccionar el medio desde la terminal y reutilizar los espacios del buffer.

3. ¿Cómo puedo usar semáforos para evitar que el productor escriba cuando el buffer está lleno y hacer que el consumidor espere cuando no hay datos? Agrega mediciones de tiempos, ocupación y espera de ambos procesos.

4. Necesito ejecutar pruebas pequeñas antes de procesar el archivo completo. ¿Cómo puedo controlar la cantidad de bloques, los espacios del buffer y los retrasos desde la terminal?

5. ¿Cómo puedo implementar las operaciones de escritura, lectura y liberación de datos de manera que el productor y el consumidor funcionen con la misma estructura, independientemente del medio seleccionado?

6. ¿Cómo puedo convertir los bloques de datos meteorológicos a un formato que permita almacenarlos y recuperarlos mediante KAX?

7. Ayúdame a guardar los resultados de cada ejecución en un archivo CSV para poder comparar posteriormente los tiempos obtenidos en los diferentes medios.

## ChatGPT — revisión, depuración y evaluación

1. Tengo un CSV meteorológico con fechas, precipitación y temperaturas. Ayúdame a revisar cuántos registros completos hay por año y a preparar archivos separados para entrenar y probar un clasificador, leyendo el CSV por bloques.

2. Quiero entrenar un clasificador de lluvia con temperaturas máxima y mínima, usando la precipitación como etiqueta y sin incluirla como variable de entrada. ¿Cómo puedo entrenar por bloques, guardar el modelo y utilizarlo sin modificarlo durante las pruebas de disco, RAM y nube?

3. Al enviar bloques a la nube mediante KAX obtengo errores al decodificar Base64. Ayúdame a revisar las respuestas del servidor y a evitar que el programa quede esperando indefinidamente si falla uno de los procesos.

4. ¿Cómo puedo medir cuántos datos se envían, cuánta memoria se reserva y cuál es la ocupación máxima del buffer, diferenciando esos valores del tamaño total del archivo?

5. Ayúdame a organizar experimentos con los mismos registros y el mismo modelo para comparar disco, RAM y nube. Quiero variar las pausas del productor y consumidor y comparar buffers de uno, dos y cuatro espacios.

6. Ayúdame a interpretar los resultados obtenidos en mi terminal, especialmente los tiempos de espera y el bloqueo que evita el desbordamiento. Explica también las limitaciones de las mediciones y del clasificador.

7. ¿Cómo puedo trabajar con una cantidad de datos mayor que la memoria disponible en el servidor remoto? Quiero enviar los datos por bloques y reutilizar los segmentos de memoria conforme se vayan liberando.

8. Ayúdame a automatizar las corridas desde la terminal de Ubuntu para ejecutar las diferentes configuraciones del productor y consumidor sin tener que introducir cada comando manualmente.

9. ¿Por qué la suma de los tiempos de escritura y lectura puede ser mayor que el tiempo total de ejecución cuando se utilizan dos procesos?


## Verificación realizada

Los programas se ejecutaron en Ubuntu y los resultados presentados en el reporte se obtuvieron de las pruebas realizadas en la terminal. Se comprobó que los tres medios procesaran la misma cantidad de registros y obtuvieran la misma exactitud de clasificación.
