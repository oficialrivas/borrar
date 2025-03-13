import subprocess
import json

def ejecutar_script(archivo, parametro):
    """Ejecuta un script con subprocess y retorna el resultado en JSON."""
    cache_key = f"{archivo}:{parametro}"

    print(f"🔍 Ejecutando scraper en {archivo} con los valores:")
    print(f"    📌 Parámetro de búsqueda: {parametro}")

    comando = ["xvfb-run", "python3", archivo, str(parametro)]
    print(f"🖥 Ejecutando comando: {' '.join(comando)}")

    try:
        result = subprocess.run(
            comando,
            capture_output=True,
            text=True
        )

        stdout, stderr = result.stdout.strip(), result.stderr.strip()

        print(f"📜 STDOUT ({archivo}): {stdout}")
        print(f"⚠️ STDERR ({archivo}): {stderr}")

        if stdout:
            return json.loads(stdout)
        else:
            return {"error": "Salida vacía"}
    except json.JSONDecodeError as e:
        return {"error": f"Error al decodificar JSON: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}
