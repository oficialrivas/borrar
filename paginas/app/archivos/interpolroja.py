import json
import asyncio
import sys
import base64
from playwright.async_api import async_playwright

async def run(playwright, apellido):
    apellido = apellido.upper()
    resultado_json = {}

    try:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.interpol.int/es/Como-trabajamos/Notificaciones/Notificaciones-rojas/Ver-las-notificaciones-rojas")

        await page.get_by_role("textbox", name="Apellidos").click()
        await page.get_by_role("textbox", name="Apellidos").fill(apellido)
        await page.get_by_role("button", name="Buscar").click()

        await page.wait_for_timeout(3000)

        resultados = page.locator(f"a:has-text('{apellido}')")
        count = await resultados.count()
        resultado_json["total_resultados"] = count

        if count == 0:
            resultado_json["error"] = f"No se encontraron resultados para '{apellido}'"
            print(json.dumps(resultado_json, indent=4, ensure_ascii=False))
            await context.close()
            await browser.close()
            return

        first_result = resultados.first
        await first_result.click()

        await page.wait_for_timeout(3000)

        async def obtener_texto(selector):
            try:
                return (await page.locator(selector).first.inner_text()).strip()
            except:
                return "No encontrado"

        datos = {
            "nombre": await obtener_texto("tr:has(td:has-text('Nombre')) td:nth-of-type(2)"),
            "apellido": await obtener_texto("tr:has(td:has-text('Apellidos')) td:nth-of-type(2)"),
            "sexo": await obtener_texto("tr:has(td:has-text('Sexo')) td:nth-of-type(2)"),
            "fecha_nacimiento": await obtener_texto("tr:has(td:has-text('Fecha de nacimiento')) td:nth-of-type(2)"),
            "lugar_nacimiento": await obtener_texto("tr:has(td:has-text('Lugar de nacimiento')) td:nth-of-type(2)"),
            "nacionalidad": await obtener_texto("tr:has(td:has-text('Nacionalidad')) td:nth-of-type(2)")
        }

        image_element = page.locator(".redNoticeLargePhoto__img").first
        image_src = await image_element.get_attribute("src") if image_element else None

        if image_src:
            image_bytes = await page.evaluate('''async (src) => {
                const response = await fetch(src);
                const buffer = await response.arrayBuffer();
                return Array.from(new Uint8Array(buffer));
            }''', image_src)
            image_data = base64.b64encode(bytes(image_bytes)).decode("utf-8")
            datos["foto"] = image_data
        else:
            datos["foto"] = "No encontrado"

        resultado_json["datos"] = datos
        print(json.dumps(resultado_json, indent=4, ensure_ascii=False))

        await context.close()
        await browser.close()

    except Exception as e:
        resultado_json["error"] = str(e)
        print(json.dumps(resultado_json, indent=4, ensure_ascii=False))

async def main():
    apellido = sys.argv[1] if len(sys.argv) > 1 else input("Ingrese el apellido a buscar: ")
    async with async_playwright() as playwright:
        await run(playwright, apellido)

if __name__ == "__main__":
    asyncio.run(main())
