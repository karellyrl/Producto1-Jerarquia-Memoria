import base64
import os
import shutil


#Almacenamiento en disco
class MedioDisco:
    nombre = "disco"

    def __init__(self, carpeta="shared_disk_memory"):
        self.carpeta = carpeta

    #Crea la carpeta
    def setup(self, n_slots):
        shutil.rmtree(self.carpeta, ignore_errors=True)
        os.makedirs(self.carpeta, exist_ok=True)

    #Escribe el bloque
    def put(self, slot, data: bytes):
        ruta = os.path.join(self.carpeta, f"slot_{slot}.bin")
        with open(ruta, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())  #Fuerza la escritura a disco
        return ruta

    #Lee el bloque
    def get(self, handle):
        with open(handle, "rb") as f:
            return f.read()

    #Borra el archivo
    def release(self, handle):
        os.remove(handle)

    #Borra la carpeta
    def teardown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)


#Memoria compartida local
class MedioRamKax:

    nombre = "ram"

    def __init__(self, slot_mb=32, prefijo="clima_shm"):
        self.slot_bytes = int(slot_mb * 1024 * 1024)
        self.prefijo = prefijo
        self._kax = None

    def _k(self):
        #Abre la conexion con KAX si aun no existe
        if self._kax is None:
            from kax import Kax
            self._kax = Kax()
        return self._kax

    #Reserva un segmento de memoria para cada espacio del buffer
    def setup(self, n_slots):
        for i in range(n_slots):
            try:
                self._k().removeShm(f"{self.prefijo}_{i}")  #Borra segmentos anteriores
            except Exception:
                pass
            self._k().makeShm(f"{self.prefijo}_{i}", self.slot_bytes)
        self.n_slots = n_slots

    #Guarda el bloque en el segmento correspondiente
    def put(self, slot, data: bytes):
        nombre = f"{self.prefijo}_{slot}"
        texto = base64.b64encode(data).decode()  #Convierte los bytes a texto para enviarlos mediante KAX
        if len(texto) > self.slot_bytes:
            raise ValueError(f"Chunk de {len(texto)/1e6:.1f} MB no cabe en el slot de "
                             f"{self.slot_bytes/1e6:.1f} MB. Sube --slot-mb o baja --chunk-rows.")
        self._k().putDataToShm(nombre, texto)
        return nombre

    #Lee el bloque
    def get(self, handle):
        texto = self._k().getDataFromShm(handle)
        if texto is None:
            raise FileNotFoundError(f"Segmento {handle} no existe")
        return base64.b64decode(texto.rstrip("\x00"))  #Quita los ceros sobrantes

    #Conserva el segmento para guardar el siguiente bloque
    def release(self, handle):
        pass  #Reutiliza el segmento

    #Borra los segmentos
    def teardown(self):
        for i in range(self.n_slots):
            try:
                self._k().removeShm(f"{self.prefijo}_{i}")
            except Exception:
                pass


#Memoria compartida remota
class MedioNubeKax:






    nombre = "nube"

    def __init__(self, slot_mb=10):
        import uuid
        self.slot_bytes = int(slot_mb * 1024 * 1024)
        #Evita que los segmentos coincidan con los de otros usuarios
        self.prefijo = f"clima_{uuid.uuid4().hex[:8]}"
        self.host = os.environ.get("KAX_HOST", "148.247.201.144")
        self.registry_port = os.environ.get("KAX_REGISTRY_PORT", "5061")
        self.storage_port = os.environ.get("KAX_STORAGE_PORT", "5071")
        self.broker_port = int(os.environ.get("KAX_BROKER_PORT", "1881"))
        self.n_slots = 0
        self._kax = None

    def _k(self):
        if self._kax is None:
            from kax import Kax
            self._kax = Kax(
                registry_url=f"http://{self.host}:{self.registry_port}/api",
                storage_url=f"http://{self.host}:{self.storage_port}/api",
                broker=self.host, port=self.broker_port, workers=1, chunk_size=2)
        return self._kax

    #Reserva un segmento de memoria para cada espacio del buffer
    def setup(self, n_slots):
        self.n_slots = n_slots
        for i in range(n_slots):
            self._k().makeShmInCloud(f"{self.prefijo}_{i}", self.slot_bytes)

    #Guarda el bloque en el segmento correspondiente
    def put(self, slot, data: bytes):
        nombre = f"{self.prefijo}_{slot}"
        texto = base64.b64encode(data).decode()
        if len(texto) > self.slot_bytes:
            raise ValueError(f"Chunk de {len(texto)/1e6:.1f} MB no cabe en el slot de "
                             f"{self.slot_bytes/1e6:.1f} MB. Sube --slot-mb o baja --chunk-rows.")
        #Revisa si el servidor pudo guardar los datos
        respuesta = self._k().putDataToShmInCloud(nombre, texto)
        if isinstance(respuesta, dict) and str(respuesta.get("message", "")).lower() == "error":
            raise RuntimeError(f"KAX nube: {respuesta}")
        return nombre

    #Lee el bloque
    def get(self, handle):
        obj = self._k().getDataFromShmInCloud(handle)

        #Comprueba que el servidor devuelva datos antes de decodificarlos
        if not isinstance(obj, (str, bytes)):
            raise RuntimeError(f"KAX nube devolvio una respuesta inesperada: {obj!r}")
        if isinstance(obj, bytes):
            obj = obj.decode("utf-8")
        return base64.b64decode(obj.rstrip("\x00"), validate=True)

    #Conserva el segmento para guardar el siguiente bloque
    def release(self, handle):
        pass  #Reutiliza el segmento

    #Borra los segmentos
    def teardown(self):
        #Limpia la memoria remota
        for i in range(self.n_slots):
            try:
                self._k().removeShmFromCloud(f"{self.prefijo}_{i}")
            except Exception:
                pass


#Opcion de Google Drive
class MedioNubeDrive:


    nombre = "drive"

    def __init__(self):
        self.folder_id = None
        self._svc = None

    #Prepara la carpeta
    def setup(self, n_slots):
        import nube_drive
        #Inicia sesion
        self.folder_id = nube_drive.carpeta_id(nube_drive.servicio())

    def _s(self):
        if self._svc is None:
            import nube_drive
            self._svc = nube_drive.servicio()
        return self._svc

    #Sube el bloque
    def put(self, slot, data: bytes):
        import nube_drive
        import time
        return nube_drive.subir(self._s(), f"chunk_{slot}_{time.time_ns()}.bin", data, self.folder_id)

    #Descarga el bloque
    def get(self, handle):
        import nube_drive
        return nube_drive.descargar(self._s(), handle)

    #Borra el archivo
    def release(self, handle):
        self._s().files().delete(fileId=handle).execute()

    #Finaliza
    def teardown(self):
        pass


#Selecciona el medio
def crear_medio(nombre, slot_mb=32):
    if nombre == "disco":
        return MedioDisco()
    if nombre == "ram":
        return MedioRamKax(slot_mb=slot_mb)
    if nombre == "nube":
        return MedioNubeKax(slot_mb=min(slot_mb, 10))
    if nombre == "drive":
        return MedioNubeDrive()
    raise ValueError("medio debe ser disco, ram, nube o drive")

