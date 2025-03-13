import json
import asyncio
import re
import sys
import os
from playwright.async_api import async_playwright

# Definir la carpeta de descargas dentro de "static"
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
os.makedirs(STATIC_DIR, exist_ok=True)

async def manejar_descarga(page, numero_rad):
    """Función para manejar la descarga o el botón de 'VOLVER' si aparece."""
    try:
        boton_descarga = page.locator("button", has_text="Descargar DOC")

        if await boton_descarga.is_visible():
            async with page.expect_request("**/api/v2/Descarga/DOCX/**") as request_info:
                await boton_descarga.click()

            # Esperar un poco a ver si aparece el botón de "VOLVER"
            await asyncio.sleep(2)
            boton_volver = page.locator("button", has_text="VOLVER")

            if await boton_volver.is_visible():
                await boton_volver.click()
                return None

            # Si no aparece el botón "VOLVER", obtenemos la URL de descarga
            request = await request_info.value
            return request.url.strip()

    except Exception:
        return None


async def run(playwright, nombre):
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(accept_downloads=True)
    page = await context.new_page()

    async def realizar_consulta():
        """Realiza la consulta inicial y devuelve la lista de números de radicación."""
        await page.goto("https://consultaprocesos.ramajudicial.gov.co/Procesos/NombreRazonSocial")

        await page.locator("div").filter(has_text=re.compile(r"^Todos los Procesos \(consulta completa, menos rápida\)$")).locator("div").nth(1).click()
        await page.get_by_role("textbox", name="* Tipo de Persona").click()
        await page.get_by_text("Natural").click()
        await page.get_by_role("textbox", name="* Nombre(s) Apellido o Razón").click()
        await page.get_by_role("textbox", name="* Nombre(s) Apellido o Razón").fill(nombre)
        await page.get_by_role("button", name="Consultar por nombre o razón social", exact=True).click()
        await page.locator("span.v-btn__content").filter(has_text="VOLVER").click()
        await page.wait_for_selector("tbody tr", timeout=5000)

        filas = page.locator("tbody tr")
        num_filas = await filas.count()
        numeros_rad = []

        for i in range(num_filas):
            filas_actualizadas = page.locator("tbody tr")
            num_rad = await filas_actualizadas.nth(i).locator("td:nth-child(2) button .v-btn__content").inner_text()
            numeros_rad.append(num_rad)

        return numeros_rad

    async def procesar_numero(numero_rad):
        """Procesa un número de radicación y extrae la información."""
        try:
            filas_actualizadas = page.locator("tbody tr")
            fila_objetivo = filas_actualizadas.filter(has_text=numero_rad).nth(0)
            boton_numero = fila_objetivo.locator("td:nth-child(2) button")

            if not await boton_numero.is_visible():
                return None

            await boton_numero.click()
            await page.wait_for_selector("div.col.col-true", timeout=5000)

            async def obtener_valor(etiqueta):
                """Extrae el valor de una celda correspondiente a la etiqueta <th>"""
                try:
                    elemento = page.locator(f"th:has-text('{etiqueta}')").first
                    fila = elemento.locator("xpath=ancestor::tr")
                    valor_td = fila.locator("td").first
                    return await valor_td.inner_text() if await valor_td.is_visible() else "No disponible"
                except:
                    return "No disponible"

            detalles = {
                "Número de Proceso": numero_rad,
                "Fecha de Radicación": await obtener_valor("Fecha de Radicación:"),
                "Despacho": await obtener_valor("Despacho:"),
                "Ponente": await obtener_valor("Ponente:"),
                "Tipo de Proceso": await obtener_valor("Tipo de Proceso:"),
                "Clase de Proceso": await obtener_valor("Clase de Proceso:"),
                "Subclase de Proceso": await obtener_valor("Subclase de Proceso:"),
                "Recurso": await obtener_valor("Recurso:"),
                "Ubicación del Expediente": await obtener_valor("Ubicación del Expediente:"),
                "Documento": None
            }

            # Sujetos Procesales
            await page.get_by_role("tab", name="Sujetos Procesales").click()
            sujetos = await page.locator("tbody tr").all_inner_texts()
            detalles["Sujetos Procesales"] = list(set(s.strip() for s in sujetos if "Cargando..." not in s))

            # Documentos del Proceso
            await page.get_by_role("tab", name="Documentos del Proceso").click()
            documentos = await page.locator("tbody tr").all_inner_texts()
            detalles["Documentos del Proceso"] = list(set(d.strip() for d in documentos if "Cargando..." not in d))

            # Actuaciones
            await page.get_by_role("tab", name="Actuaciones").click()
            actuaciones = await page.locator("tbody tr").all_inner_texts()
            detalles["Actuaciones"] = list(set(a.strip() for a in actuaciones if "Cargando..." not in a))

            # Volver a la lista con el botón "Regresar al listado"
            try:
                boton_regresar = page.locator("button").filter(has_text="Regresar al listado")
                await boton_regresar.wait_for(state="visible", timeout=7000)
                await boton_regresar.click()
                await page.wait_for_load_state("networkidle")
            except:
                await page.go_back()
                await page.wait_for_load_state("networkidle")

            return detalles

        except Exception:
            return None

    # Ejecutar scraping en todos los procesos
    datos = []
    numeros_rad = await realizar_consulta()

    if not numeros_rad:
        resultado_json = {"mensaje": f"No se encontraron procesos judiciales para '{nombre}'."}
    else:
        for numero in numeros_rad:
            resultado = await procesar_numero(numero)
            if resultado:
                datos.append(resultado)

    # Obtener URLs de documentos después de haber procesado todos los números
    async def obtener_urls_documentos():
        for proceso in datos:
            if proceso.get("Número de Proceso"):
                proceso["Documento"] = await manejar_descarga(page, proceso["Número de Proceso"])

    await obtener_urls_documentos()

    resultado_json = {"procesos": datos}

    # **Salida JSON limpia sin logs extra**
    print(json.dumps(resultado_json, indent=4, ensure_ascii=False))

    await context.close()
    await browser.close()

    return resultado_json

async def main():
    nombre = sys.argv[1] if len(sys.argv) > 1 else input("Ingrese el nombre completo a buscar: ")
    
    async with async_playwright() as playwright:
        await run(playwright, nombre)

if __name__ == "__main__":
    asyncio.run(main())
