import json
import asyncio
import sys
from playwright.async_api import async_playwright

async def run(playwright, documento):
    resultado_json = {}

    try:
        browser = await playwright.chromium.launch(headless=False)  # Cambia a True si no necesitas ver la ejecución
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.libretamilitar.mil.co/Modules/Consult/MilitarySituation")

        # Seleccionar Tipo de Documento
        await page.get_by_label("Tipo de documento (*):").select_option("100000001")

        # Llenar Número de Documento
        await page.get_by_role("textbox", name="Número de documento (*):").fill(documento)

        # Hacer clic en Consultar
        await page.get_by_role("button", name="Consultar").click()

        # Esperar a que cargue la tarjeta de información
        await page.wait_for_selector("#divConsult", timeout=100000)

        async def obtener_texto(selector):
            try:
                return (await page.locator(selector).first.inner_text()).strip()
            except:
                return "No encontrado"

        # Extraer datos requeridos
        datos = {
            "nombre": await obtener_texto("#ctl00_MainContent_lblDefinedName"),
            "estado_militar": await obtener_texto("#ctl00_MainContent_lblDefinedState"),
            "distrito_militar": await obtener_texto("#ctl00_MainContent_lblDefinedPlaceText"),
            "direccion": await obtener_texto("#ctl00_MainContent_lblDefinedAdressText"),
        }

        resultado_json["datos"] = datos
        print(json.dumps(resultado_json, indent=4, ensure_ascii=False))

        await context.close()
        await browser.close()

    except Exception as e:
        resultado_json["error"] = str(e)
        print(json.dumps(resultado_json, indent=4, ensure_ascii=False))

async def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Se requiere un número de documento."}, indent=4, ensure_ascii=False))
        sys.exit(1)

    documento = sys.argv[1]
    async with async_playwright() as playwright:
        await run(playwright, documento)

if __name__ == "__main__":
    asyncio.run(main())
