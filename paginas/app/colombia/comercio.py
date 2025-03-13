import base64
import time
import requests
import json
import sys
from playwright.sync_api import Playwright, sync_playwright

API_KEY = "beff1a3bcf68e4fcd8a9c0b1c2169f45"

# Función para convertir imagen a base64
def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Función para resolver captcha con 2Captcha
def solve_captcha(image_path):
    while True:  # Reintentar hasta que el captcha se resuelva correctamente
        try:
            image_base64 = encode_image_to_base64(image_path)

            response = requests.post("http://2captcha.com/in.php", data={
                "key": API_KEY,
                "method": "base64",
                "body": image_base64,
                "json": 1
            })

            request_result = response.json()
            if request_result.get("status") != 1:
                continue  # Reintentar si el envío del captcha falla
            
            captcha_id = request_result["request"]

            # Esperar la respuesta del captcha
            for _ in range(10):  
                time.sleep(5)
                result_response = requests.get(f"http://2captcha.com/res.php?key={API_KEY}&action=get&id={captcha_id}&json=1")
                result = result_response.json()
                
                if result.get("status") == 1:
                    return result["request"]

        except Exception:
            continue  # Reintentar en caso de error

def run(playwright: Playwright, identificacion):
    try:
        browser = playwright.chromium.launch(headless=False)  # Mantiene el navegador visible
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://serviciospub.sic.gov.co/Sic2/Tramites/Radicacion/Radicacion/Consultas/ConsultaRadicacion.php")

        # Aceptar advertencia si aparece
        try:
            page.get_by_role("link", name="Entendido").click()
        except:
            pass

        # Seleccionar tipo de documento y número
        page.locator("select[name=\"fdocumento\"]").select_option("CC")
        page.locator("input[name=\"fnumero\"]").fill(identificacion)

        while True:  # Reintentar hasta que el captcha sea válido
            # Capturar y resolver captcha
            captcha_path = "captcha.png"
            page.locator("#siimage").screenshot(path=captcha_path)
            captcha_text = solve_captcha(captcha_path)

            if captcha_text:
                page.locator("input[name=\"captcha\"]").fill(captcha_text)
                page.get_by_role("button", name="Consultar").click()
                page.wait_for_timeout(5000)

                # Verificar si el captcha falló
                if page.locator("text=La validación del CAPTCHA ha fallado").is_visible():
                    continue  # Reintentar todo el proceso

                break  # Si el captcha es válido, continuar

        # Extraer datos de la tabla asegurando que se capturan correctamente
        filas = page.locator("#tablaResultados tbody tr").all()
        resultados = {}

        for fila in filas:
            celdas = fila.locator("td").all_text_contents()

            if len(celdas) > 1:  # Asegurar que la fila no esté vacía
                datos_lista = [c.strip().replace("\n", " ").replace("  ", " ") for c in celdas if c.strip()]
                
                # Asignar valores en el orden correcto
                estructura = [
                    "Año", "Número", "Ctrl", "Cons Rad", "Sec Eve", 
                    "Evento", "Actuación", "Tipo", "Fecha", "Solicitante"
                ]
                
                # Limitar la asignación para evitar desbordes en los índices
                resultado = {estructura[i]: datos_lista[i] if i < len(datos_lista) else "" for i in range(len(estructura))}

                # Extraer la URL de descarga
                enlace_descarga = None
                enlaces = fila.locator("td a").all()
                for link in enlaces:
                    href = link.get_attribute("href")
                    if href and "BuscardoPrueba" in href:
                        enlace_descarga = href
                        break

                resultado["URL Descarga"] = enlace_descarga if enlace_descarga else "No disponible"

                # Agregar resultado al diccionario con un identificador único
                resultados[resultado["Número"]] = resultado

        context.close()
        browser.close()

        # Retornar JSON limpio como un **objeto JSON**, sin lista []
        return json.dumps(resultados, indent=4, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Se requiere un número de identificación."}, indent=4, ensure_ascii=False))
        sys.exit(1)

    identificacion = sys.argv[1]

    with sync_playwright() as playwright:
        resultado = run(playwright, identificacion)
        print(resultado)  # Solo imprime el JSON limpio
