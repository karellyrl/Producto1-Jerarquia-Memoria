import argparse
import csv as csvlib
import os
import time
from multiprocessing import Process, Queue, Semaphore, Value, Manager

from clima import Clasificador, deserializar, leer_chunks, serializar
from medios import crear_medio


#El productor lee el CSV y envia cada bloque al medio seleccionado
def productor(args, medio, vacios, cola, stats):
    t_bloq = t_put = 0.0
    n = 0
    for df in leer_chunks(args.csv, args.chunk_rows, args.max_chunks):
        #Convierte el bloque a bytes para poder guardarlo
        data = serializar(df)
        if args.prod_delay:
            time.sleep(args.prod_delay)  #Simula un productor lento
        t0 = time.perf_counter()
        vacios.acquire()  #Espera si el buffer esta lleno para no sobrescribir datos
        t_bloq += time.perf_counter() - t0
        t0 = time.perf_counter()
        handle = medio.put(n % args.slots, data)
        t_put += time.perf_counter() - t0
        #Calcula cuantos bytes ocupa el bloque en cada medio
        tam = 4 * ((len(data)+2)//3) if args.medio in ("ram", "nube") else len(data)
        #Actualiza los espacios ocupados y la cantidad de datos en el buffer
        with stats["ocupados"].get_lock():
            stats["bytes_total"].value += tam
            stats["bytes_actual"].value += tam
            stats["bytes_max"].value = max(stats["bytes_max"].value, stats["bytes_actual"].value)
            stats["ocupados"].value += 1
            stats["max_ocupados"].value = max(stats["max_ocupados"].value, stats["ocupados"].value)
        #Avisa al consumidor donde quedaron guardados los datos
        cola.put((handle, tam))
        n += 1
    cola.put(None)  #Fin de los datos
    stats["prod_bloqueado"].value = t_bloq
    stats["t_put"].value = t_put
    stats["chunks"].value = n


#El consumidor recupera los bloques y clasifica los registros
def consumidor(args, medio, vacios, cola, stats, resultado):
    clf = Clasificador()
    t_espera = t_get = t_proc = 0.0
    while True:
        t0 = time.perf_counter()
        handle = cola.get()  #Espera hasta que el productor envie un bloque
        t_espera += time.perf_counter() - t0
        if handle is None:
            break
        t0 = time.perf_counter()
        handle, tam = handle
        data = medio.get(handle)
        t_get += time.perf_counter() - t0
        #Libera el espacio despues de recuperar los datos
        medio.release(handle)
        #Actualiza los espacios ocupados y la cantidad de datos en el buffer
        with stats["ocupados"].get_lock():
            stats["ocupados"].value -= 1
            stats["bytes_actual"].value -= tam
        vacios.release()  #Permite que el productor vuelva a utilizar el espacio
        t0 = time.perf_counter()
        clf.procesar(deserializar(data))
        if args.cons_delay:
            time.sleep(args.cons_delay)  #Simula un consumidor lento
        t_proc += time.perf_counter() - t0
    stats["cons_espera"].value = t_espera
    stats["t_get"].value = t_get
    stats["t_proc"].value = t_proc
    resultado.update(clf.resumen())


#Prepara el medio, el buffer y los dos procesos
def run_pipeline(args):
    medio = crear_medio(args.medio, args.slot_mb)
    medio.setup(args.slots)
    vacios = Semaphore(args.slots)
    cola = Queue()
    #Guarda los tiempos y conteos que usan ambos procesos
    stats = {k: Value("d", 0.0) for k in
             ["prod_bloqueado", "t_put", "cons_espera", "t_get", "t_proc"]}
    stats.update({k: Value("i", 0) for k in ["ocupados", "max_ocupados", "chunks"]})
    stats.update({k: Value("q", 0) for k in ["bytes_total", "bytes_actual", "bytes_max"]})
    mgr = Manager()
    resultado = mgr.dict()
    try:
        t0 = time.perf_counter()
        p1 = Process(target=productor, args=(args, medio, vacios, cola, stats))
        p2 = Process(target=consumidor, args=(args, medio, vacios, cola, stats, resultado))
        #Inicia los procesos
        p1.start(); p2.start()
        try:
            #Detecta si alguno de los procesos termino con error
            while p1.is_alive() or p2.is_alive():
                if any(p.exitcode not in (None, 0) for p in (p1,p2)):
                    raise RuntimeError("Fallo un proceso del pipeline")
                time.sleep(0.05)
            if any(p.exitcode != 0 for p in (p1,p2)):
                raise RuntimeError("Fallo un proceso del pipeline")
        finally:
            for p in (p1,p2):
                if p.is_alive(): p.terminate()
                p.join()
        total = time.perf_counter() - t0
    finally:
        #Limpia el medio
        medio.teardown()
    #Reune los tiempos y resultados de la corrida
    fila = {
        "modo": f"buffer-{args.medio}", "slots": args.slots,
        "prod_delay": args.prod_delay, "cons_delay": args.cons_delay,
        "chunks": stats["chunks"].value, "total_s": round(total, 3),
        "transfer_s": round(stats["t_put"].value + stats["t_get"].value, 3),
        "put_s": round(stats["t_put"].value, 3),
        "get_s": round(stats["t_get"].value, 3),
        "proc_s": round(stats["t_proc"].value, 3),
        "prod_bloqueado_s": round(stats["prod_bloqueado"].value, 3),
        "cons_espera_s": round(stats["cons_espera"].value, 3),
        "max_ocupacion": stats["max_ocupados"].value,
        "mib_enviados": round(stats["bytes_total"].value/1048576, 4),
        "mib_max_buffer": round(stats["bytes_max"].value/1048576, 4),
        "mib_reservados": round(getattr(medio, "slot_bytes", 0)*args.slots/1048576, 4) if hasattr(medio, "slot_bytes") else None,
    }
    fila.update(dict(resultado))
    mgr.shutdown()
    return fila


#Procesa los bloques directamente para comparar con el pipeline
def run_secuencial(args):

    clf = Clasificador()
    t0 = time.perf_counter()
    n = 0
    for df in leer_chunks(args.csv, args.chunk_rows, args.max_chunks):
        if args.prod_delay:
            time.sleep(args.prod_delay)
        clf.procesar(df)
        if args.cons_delay:
            time.sleep(args.cons_delay)
        n += 1
    #Reune los tiempos y resultados de la corrida
    fila = {"modo": "secuencial", "slots": 0, "prod_delay": args.prod_delay,
            "cons_delay": args.cons_delay, "chunks": n,
            "total_s": round(time.perf_counter() - t0, 3)}
    fila.update(clf.resumen())
    return fila


#Muestra los resultados
def mostrar(fila):
    print("\n" + "-" * 60)
    for k, v in fila.items():
        print(f"  {k:18} {v}")
    print("-" * 60)


#Guarda los resultados en CSV
def guardar(filas, ruta="resultados_nuevos.csv"):
    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", newline="") as f:
        campos = ["modo", "slots", "prod_delay", "cons_delay", "chunks", "total_s", "transfer_s", "put_s", "get_s", "proc_s",
                  "prod_bloqueado_s", "cons_espera_s", "max_ocupacion", "filas", "pct_lluvia", "accuracy", "mib_enviados", "mib_max_buffer", "mib_reservados"]
        w = csvlib.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        if nuevo:
            w.writeheader()
        w.writerows(filas)


#Lee las opciones que se indican en la terminal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comando", choices=["run", "secuencial", "experimento"])
    ap.add_argument("--csv", required=True)
    ap.add_argument("--medio", default="ram", choices=["disco", "ram", "nube", "drive"])
    ap.add_argument("--slots", type=int, default=4, help="capacidad del buffer (chunks)")
    ap.add_argument("--chunk-rows", type=int, default=100_000)
    ap.add_argument("--max-chunks", type=int, default=20, help="0 = todo el archivo")
    ap.add_argument("--slot-mb", type=float, default=32, help="tamano del segmento kax por slot")
    ap.add_argument("--prod-delay", type=float, default=0.0, help="seg extra por chunk del productor")
    ap.add_argument("--cons-delay", type=float, default=0.0, help="seg extra por chunk del consumidor")
    args = ap.parse_args()

    filas = []
    if args.comando == "secuencial":
        filas.append(run_secuencial(args))
    elif args.comando == "run":
        filas.append(run_pipeline(args))
    else:
        #Cambia las pausas para simular distintas velocidades de procesamiento
        for pd_, cd in [(0.0, 0.0), (0.0, 0.2), (0.1, 0.1), (0.2, 0.0)]:
            args.prod_delay, args.cons_delay = pd_, cd
            filas.append(run_secuencial(args))
            for medio in ("disco", "ram"):
                args.medio = medio
                for slots in (1, 4):
                    args.slots = slots
                    filas.append(run_pipeline(args))
    for f in filas:
        mostrar(f)
    guardar(filas)
    print("\nResultados agregados a resultados_nuevos.csv")


if __name__ == "__main__":
    main()
