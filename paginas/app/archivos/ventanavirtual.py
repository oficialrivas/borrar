import asyncio
import json
import time
import requests
import sys
from playwright.async_api import async_playwright

API_KEY = "beff1a3bcf68e4fcd8a9c0b1c2169f45"
URL = "https://servicios.supersociedades.gov.co/barandaVirtual/#!/app/procesos"

HEADERS_PERMITIDOS = {
    "DATOS BÁSICOS",
    "ACTIVIDAD ECONÓMICA",
    "DIRECCIÓN DE CORRESPONDENCIA",
    "DIRECCIÓN DE DOMICILIO",
    "SITUACIÓN / ESTADO",
    "ADMINISTRADORES / REPRESENTANTES"
}

async def solve_recaptcha_v2(site_key, url):
    """Resuelve reCAPTCHA v2 usando 2Captcha."""
    try:
        response = requests.post("http://2captcha.com/in.php", data={
            "key": API_KEY,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": url,
            "json": 1
        })
        result = response.json()
        if result.get("status") != 1:
            return None

        captcha_id = result["request"]
        for _ in range(15):  # Máximo 75 segundos (15 x 5s)
            time.sleep(5)
            solution_response = requests.get(f"http://2captcha.com/res.php?key={API_KEY}&action=get&id={captcha_id}&json=1")
            solution_result = solution_response.json()

            if solution_result.get("status") == 1:
                return solution_result["request"]

        return None
    except Exception:
        return None

async def extract_table_data(page):
    """Extrae los datos de las tablas permitidas y los estructura en formato clave-valor limpio."""
    data = {}
    headers = await page.locator("h4").all_text_contents()

    for header in headers:
        header = header.strip().upper()
        if header in HEADERS_PERMITIDOS:
            table_locator = page.locator(f"h4:has-text('{header}') + table tbody")
            if await table_locator.count() > 0:
                table_data = {}

                rows = await table_locator.locator("tr").all()
                for row in rows:
                    columns = await row.locator("td").all_text_contents()
                    clean_columns = [col.strip().replace("\n", " ").replace("  ", " ") for col in columns if col.strip()]

                    if len(clean_columns) == 2:
                        key, value = clean_columns
                        table_data[key] = value
                    elif len(clean_columns) > 2:
                        table_data[clean_columns[0]] = ", ".join(clean_columns[1:])

                data[header] = table_data

    return data

async def extract_document_url(page):
    """Extrae la URL del documento dentro del visor asegurando que no devuelva 'null'."""
    try:
        embed_element = await page.wait_for_selector("div#pdf.ng-binding embed", timeout=15000)
        url = await embed_element.get_attribute("src")
        return url if url else None
    except:
        return None

async def extract_row_data(row):
    """Extrae los datos de una fila de la tabla de manera limpia."""
    columns = [col.strip().replace("\n", " ").replace("  ", " ") for col in await row.locator("td").all_text_contents() if col.strip()]
    return columns

async def process_radicacion(page, radicacion_link):
    """Procesa una radicación para extraer la URL del documento."""
    try:
        await radicacion_link.scroll_into_view_if_needed()
        await radicacion_link.click(force=True)
        await page.wait_for_load_state("networkidle", timeout=10000)
        return await extract_document_url(page)
    except:
        return None

async def extract_table_rows(page, table_selector):
    """Extrae todas las filas de una tabla y sus respectivas URLs."""
    filas = await page.locator(f"{table_selector} tbody tr").all()
    resultados = []

    for fila in filas:
        datos_fila = await extract_row_data(fila)
        radicacion_link = fila.locator("button.btn-link, a").first

        url_documento = None
        if await radicacion_link.count() > 0:
            url_documento = await process_radicacion(page, radicacion_link)

        resultados.append({
            "Datos de la fila": datos_fila,
            "URL del documento": url_documento
        })

    return resultados

async def run(playwright, razon_social):
    """Ejecuta el proceso principal de Playwright."""
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(URL)

    # ✅ Aceptar políticas y seleccionar búsqueda
    await page.locator("input[name='politica']").check()
    await page.select_option("#tipo_busqueda", "rsocial")
    await page.fill("input[name='buscador']", razon_social)

    # ✅ Resolver CAPTCHA antes de hacer clic en "Buscar"
    recaptcha_iframe = await page.locator("iframe[title='reCAPTCHA']").get_attribute("src")
    site_key = recaptcha_iframe.split("k=")[1].split("&")[0] if recaptcha_iframe else None

    if site_key:
        captcha_response = await solve_recaptcha_v2(site_key, URL)
        if captcha_response:
            await page.evaluate(f"document.getElementById('g-recaptcha-response').innerHTML = '{captcha_response}';")

    # ✅ Hacer clic en "Buscar"
    boton_buscar = page.locator("input#submit")
    await boton_buscar.wait_for(state="visible", timeout=7000)
    await boton_buscar.click(force=True)
    await page.wait_for_load_state("networkidle", timeout=15000)

    # ✅ Esperar y hacer clic en el NIT
    await page.wait_for_selector("div.col-md-6.ng-scope a.ng-binding", timeout=15000)

    nit_link = page.locator("div.col-md-6.ng-scope a.ng-binding").first
    if not await nit_link.count():
        return

    await nit_link.scroll_into_view_if_needed()
    await nit_link.click(force=True)
    await page.wait_for_load_state("networkidle", timeout=10000)

    # ✅ Extraer datos de "Resumen de Sociedades"
    resumen_sociedades = await extract_table_data(page)

    # ✅ Extraer datos de "Consulta Providencias"
    await page.locator("a:has-text('Consulta Providencias')").click()
    await page.wait_for_selector("table#DataTables_Table_0 tbody", timeout=15000)
    consulta_providencias = await extract_table_rows(page, "table#DataTables_Table_0")

    # ✅ Extraer datos de "Radicaciones de Entrada"
    await page.locator("a:has-text('Radicaciones de Entrada')").click()
    await page.wait_for_selector("table#DataTables_Table_1 tbody", timeout=15000)
    radicaciones_entrada = await extract_table_rows(page, "table#DataTables_Table_1")

    # ✅ Imprimir solo el JSON sin logs adicionales
    resultados_finales = {
        "Resumen de Sociedades": resumen_sociedades,
        "Consulta Providencias": consulta_providencias,
        "Radicaciones de Entrada": radicaciones_entrada
    }

    print(json.dumps(resultados_finales, indent=4, ensure_ascii=False))

    await browser.close()

async def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Se requiere una razón social."}, indent=4, ensure_ascii=False))
        sys.exit(1)

    razon_social = " ".join(sys.argv[1:])  # Combina los argumentos sin comillas

    async with async_playwright() as playwright:
        await run(playwright, razon_social)

if __name__ == "__main__":
    asyncio.run(main())
