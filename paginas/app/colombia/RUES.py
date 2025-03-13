import json
import asyncio
import sys
from playwright.async_api import async_playwright

async def run(playwright, cedula):
    resultado_json = {}

    try:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://ruesfront.rues.org.co/busqueda-avanzada")

        await page.get_by_placeholder("identificacion").fill(cedula)
        await page.get_by_role("button", name="Buscar").click()

        await page.wait_for_timeout(500)
        await page.get_by_role("link", name="Ver información").click()
        await page.wait_for_timeout(500)

        async def obtener_texto(selector):
            try:
                return (await page.locator(selector).first.inner_text()).strip()
            except:
                return "No encontrado"

        nombre_completo = await obtener_texto("h1.intro__nombre.intro__nombre--xs")
        data_blocks = page.locator("div.col-6.col-md-6.resultado__datos")

        resultado_json["nombre"] = nombre_completo
        for i in range(await data_blocks.count()):
            etiquetas = await data_blocks.nth(i).locator("p.registroapi__etiqueta.font-rues-small").all_inner_texts()
            valores = await data_blocks.nth(i).locator("p.registroapi__valor").all_inner_texts()
            for etiqueta, valor in zip(etiquetas, valores):
                resultado_json[etiqueta.strip()] = valor.strip()

        print(json.dumps(resultado_json, indent=4, ensure_ascii=False))

        await context.close()
        await browser.close()

    except Exception as e:
        resultado_json["error"] = str(e)
        print(json.dumps(resultado_json, indent=4, ensure_ascii=False))

async def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Se requiere un número de cédula."}, indent=4, ensure_ascii=False))
        sys.exit(1)

    cedula = sys.argv[1]
    async with async_playwright() as playwright:
        await run(playwright, cedula)

if __name__ == "__main__":
    asyncio.run(main())
