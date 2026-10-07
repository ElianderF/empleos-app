import os
import re
import httpx
import psycopg
from datetime import datetime

# ---------- CONEXIÓN A POSTGRES ----------
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise SystemExit("❌ Falta DATABASE_URL en las variables de entorno.")


# ---------- FUNCIONES AUXILIARES ----------
def limpiar_html(html: str) -> str:
    if not html:
        return ""
    texto = re.sub(r"<[^>]+>", " ", html)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()[:5000]


def extraer_tags(titulo: str, descripcion: str) -> list[str]:
    catalogo = [
        "react", "node", "python", "django", "java", "aws", "docker",
        "kubernetes", "typescript", "vue", "angular", "php", "laravel",
        "sql", "mongodb", "figma", "marketing", "sales", "devops",
        "golang", "rust", "swift", "kotlin", "flutter", "nextjs",
    ]
    texto = f"{titulo} {descripcion}".lower()
    encontrados = []
    for tag in catalogo:
        if re.search(rf"\b{re.escape(tag)}\b", texto):
            encontrados.append(tag)
    return encontrados


# ---------- FUENTE 1: REMOTIVE ----------
def scrape_remotive() -> list[dict]:
    print("→ Scrapeando Remotive...")
    try:
        r = httpx.get(
            "https://remotive.com/api/remote-jobs?limit=100",
            timeout=30,
            headers={"User-Agent": "MiAppDeEmpleos/1.0"},
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []

    trabajos = []
    for j in data.get("jobs", []):
        descripcion = limpiar_html(j.get("description", ""))
        trabajos.append({
            "external_id": str(j.get("id")),
            "source": "remotive",
            "titulo": j.get("title", "").strip(),
            "empresa": j.get("company_name", "").strip(),
            "descripcion": descripcion,
            "modalidad": "remoto",
            "ubicacion": j.get("candidate_required_location", ""),
            "pais": j.get("candidate_required_location", ""),
            "categoria": j.get("category", ""),
            "tags": extraer_tags(j.get("title", ""), descripcion),
            "salario_texto": j.get("salary", "") or "",
            "tipo_contrato": j.get("job_type", "") or "",
            "url_origen": j.get("url", ""),
            "logo_url": j.get("company_logo", "") or "",
            "publicado_en": j.get("publication_date"),
        })
    print(f"  ✅ {len(trabajos)} trabajos obtenidos")
    return trabajos


# ---------- FUENTE 2: REMOTEOK ----------
def scrape_remoteok() -> list[dict]:
    print("→ Scrapeando RemoteOK...")
    try:
        r = httpx.get(
            "https://remoteok.com/api",
            timeout=30,
            headers={"User-Agent": "MiAppDeEmpleos/1.0"},
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []

    trabajos = []
    for j in data[1:]:
        descripcion = limpiar_html(j.get("description", ""))
        tags = j.get("tags", []) or []
        tags = [t.lower() for t in tags if isinstance(t, str)]
        trabajos.append({
            "external_id": str(j.get("id")),
            "source": "remoteok",
            "titulo": j.get("position", "").strip(),
            "empresa": j.get("company", "").strip(),
            "descripcion": descripcion,
            "modalidad": "remoto",
            "ubicacion": j.get("location", "") or "",
            "pais": j.get("location", "") or "",
            "categoria": "",
            "tags": tags,
            "salario_texto": str(j.get("salary", "") or ""),
            "tipo_contrato": "",
            "url_origen": j.get("url", "") or "",
            "logo_url": j.get("company_logo", "") or "",
            "publicado_en": j.get("date"),
        })
    print(f"  ✅ {len(trabajos)} trabajos obtenidos")
    return trabajos


# ---------- GUARDAR EN POSTGRES ----------
def guardar_trabajos(trabajos: list[dict]):
    if not trabajos:
        print("⚠️  No hay trabajos para guardar.")
        return

    # Quitar duplicados internos por (source, external_id)
    vistos = set()
    unicos = []
    for t in trabajos:
        clave = (t["source"], t["external_id"])
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(t)

    sql = """
        insert into jobs (
            external_id, source, titulo, empresa, descripcion,
            modalidad, ubicacion, pais, categoria, tags,
            salario_texto, tipo_contrato, url_origen, logo_url, publicado_en
        )
        values (
            %(external_id)s, %(source)s, %(titulo)s, %(empresa)s, %(descripcion)s,
            %(modalidad)s, %(ubicacion)s, %(pais)s, %(categoria)s, %(tags)s,
            %(salario_texto)s, %(tipo_contrato)s, %(url_origen)s, %(logo_url)s, %(publicado_en)s
        )
        on conflict (source, external_id) do update set
            titulo = excluded.titulo,
            empresa = excluded.empresa,
            descripcion = excluded.descripcion,
            modalidad = excluded.modalidad,
            ubicacion = excluded.ubicacion,
            pais = excluded.pais,
            categoria = excluded.categoria,
            tags = excluded.tags,
            salario_texto = excluded.salario_texto,
            tipo_contrato = excluded.tipo_contrato,
            url_origen = excluded.url_origen,
            logo_url = excluded.logo_url,
            publicado_en = excluded.publicado_en,
            scrapeado_en = now(),
            activo = true
    """

    # Normalizar publicado_en: quitar None y strings vacíos
    for t in unicos:
        if not t.get("publicado_en"):
            t["publicado_en"] = None

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for t in unicos:
                cur.execute(sql, t)
        conn.commit()

    print(f"💾 {len(unicos)} trabajos guardados/actualizados en Postgres.")


# ---------- MAIN ----------
if __name__ == "__main__":
    print("🚀 Iniciando scraping de ofertas de empleo...\n")
    todos = []
    todos.extend(scrape_remotive())
    todos.extend(scrape_remoteok())
    print(f"\n📊 Total recolectado: {len(todos)} trabajos")
    guardar_trabajos(todos)
    print("\n✅ Proceso terminado.")