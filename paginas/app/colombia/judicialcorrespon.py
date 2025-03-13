import json
import asyncio
import sys
import re
from playwright.async_api import async_playwright

async def run(playwright, numero_radicacion):
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    async def realizar_consulta(numero_rad):
        """Realiza la consulta usando el número de radicación"""
        await page.goto("https://consultaprocesos.ramajudicial.gov.co/Procesos/NumeroRadicacion")

        # Seleccionar opción "Todos los Procesos (consulta completa, menos rápida)"
        await page.locator("div").filter(has_text=re.compile(r"^Todos los Procesos \(consulta completa, menos rápida\)$")).locator("div").nth(1).click()

        # Ingresar número de radicación
        await page.get_by_role("textbox", name="Ingrese los 23 dígitos del nú").fill(numero_rad)

        # Hacer clic en "Consultar Número de radicación"
        await page.get_by_role("button", name="Consultar Número de radicación").click()

        await page.wait_for_selector("tbody tr", timeout=5000)  # Esperar a que cargue la tabla

        # Extraer números de radicación
        filas = page.locator("tbody tr")
        numeros_rad = [await filas.nth(i).locator("td:nth-child(2) button .v-btn__content").inner_text() for i in range(await filas.count())]
        
        return numeros_rad

    async def procesar_numero(numero_rad):
        """Procesa un número de radicación y extrae la información"""
        await page.wait_for_selector("tbody tr", timeout=5000)  # Asegurar que la tabla está cargada

        filas_actualizadas = page.locator("tbody tr")
        fila_objetivo = filas_actualizadas.filter(has_text=numero_rad).nth(0)
        boton_numero = fila_objetivo.locator("td:nth-child(2) button")

        if not await boton_numero.is_visible():
            return None

        try:
            await boton_numero.click()
        except:
            await boton_numero.click(force=True)

        await page.wait_for_selector("div.col.col-true", timeout=5000)

        async def obtener_valor(etiqueta):
            """Obtiene el valor de la celda <td> correspondiente a la etiqueta <th> en la misma fila"""
            elemento = page.locator(f"th:has-text('{etiqueta}')").first
            fila = elemento.locator("xpath=ancestor::tr")
            return await fila.locator("td").first.inner_text()

        detalles = {
            "Número de Proceso": numero_rad,
            "Fecha de Radicación": await obtener_valor("Fecha de Radicación:"),
            "Despacho": await obtener_valor("Despacho:"),
            "Ponente": await obtener_valor("Ponente:"),
            "Tipo de Proceso": await obtener_valor("Tipo de Proceso:"),
            "Clase de Proceso": await obtener_valor("Clase de Proceso:"),
            "Subclase de Proceso": await obtener_valor("Subclase de Proceso:"),
            "Recurso": await obtener_valor("Recurso:"),
            "Ubicación del Expediente": await obtener_valor("Ubicación del Expediente:")
        }

        # Sujetos Procesales
        await page.get_by_role("tab", name="Sujetos Procesales").click()
        await page.wait_for_selector("tbody tr", timeout=5000)
        detalles["Sujetos Procesales"] = list(set(s.strip() for s in await page.locator("tbody tr").all_inner_texts() if "Cargando..." not in s))

        # Documentos del Proceso
        await page.get_by_role("tab", name="Documentos del Proceso").click()
        await page.wait_for_selector("tbody tr", timeout=5000)
        detalles["Documentos del Proceso"] = list(set(d.strip() for d in await page.locator("tbody tr").all_inner_texts() if "Cargando..." not in d))

        # Actuaciones
        await page.get_by_role("tab", name="Actuaciones").click()
        await page.wait_for_selector("tbody tr", timeout=5000)
        detalles["Actuaciones"] = list(set(a.strip() for a in await page.locator("tbody tr").all_inner_texts() if "Cargando..." not in a))

        # Extraer URL del documento
        detalles["Documento"] = await manejar_descarga(page)

        # Volver a la lista
        try:
            boton_regresar = page.locator("button").filter(has_text="Regresar al listado")
            await boton_regresar.wait_for(state="visible", timeout=7000)
            await boton_regresar.click()
            await page.wait_for_selector("tbody tr", timeout=7000)
        except:
            await page.go_back()
            await page.wait_for_selector("tbody tr", timeout=7000)

        return detalles

    async def manejar_descarga(page):
        """Obtiene la URL del documento asociado al proceso"""
        try:
            boton_descargar = page.locator("button").filter(has_text="Descargar Documento").nth(0)
            await boton_descargar.wait_for(state="visible", timeout=5000)
            return await boton_descargar.get_attribute("href") or "No disponible"
        except:
            return "No disponible"

    # Procesar todos los números de radicación
    numeros_rad = await realizar_consulta(numero_radicacion)

    datos = [await procesar_numero(numero) for numero in numeros_rad if await procesar_numero(numero)]

    json_result = json.dumps({"procesos": datos}, indent=4, ensure_ascii=False)

    await context.close()
    await browser.close()

    return json_result

async def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Se requiere un número de radicación."}, indent=4, ensure_ascii=False))
        sys.exit(1)

    numero_radicacion = sys.argv[1]
    async with async_playwright() as playwright:
        resultado = await run(playwright, numero_radicacion)
        print(resultado)  # Solo imprime el JSON limpio

if __name__ == "__main__":
    asyncio.run(main())
