from collections import defaultdict

def normalizar_nombre(nombre):
    """Convierte un nombre en una cadena ordenada de caracteres sin importar el orden"""
    return "".join(sorted(nombre.replace(" ", "").lower()))

def agrupar_nombres_por_similitud(nombres):
    """
    Agrupa nombres que contienen los mismos caracteres sin importar el orden.
    Retorna un diccionario donde la clave es el nombre normalizado.
    """
    nombres_dict = defaultdict(list)
    for nombre in nombres:
        nombres_dict[normalizar_nombre(nombre)].append(nombre)
    return nombres_dict
