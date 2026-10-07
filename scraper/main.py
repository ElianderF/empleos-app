import os
import re
import httpx
from datetime import datetime
from supabase import create_client

# ---------- CONEXIÓN A SUPABASE ----------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("❌ Faltan SUPABASE_URL o SUPABASE_KEY en las variables de entorno.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------- FUNCIONES AUXILIARES ----------
def limpiar_html(html: str) -> str:
    """Quita las etiquetas HTML de la descripción."""
    if not html:
        return ""
    texto = re.sub(r"<[^>]+>", " ", html)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()[:5000]


def detectar_modalidad(texto: str) -> str:
    t = (texto or "").lower()
    if "remote" in t or "remoto" in t:
        return "remoto"
    if "hybrid" in t or "hibrido" in t:
        return "hibrido"
    return "presencial"


def extraer_tags(titulo: str, descripcion: str) -> list[str]:
    """Busca tecnologías conocidas en el título y la descripción."""
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
    # El primer elemento del array es un aviso legal, no un trabajo
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


# ---------- GUARDAR EN SUPABASE ----------
def guardar_trabajos(trabajos: list[dict]):
    if not trabajos:
        print("⚠️  No hay trabajos para guardar.")
        return

    # Quitamos duplicados internos (mismo source+external_id) antes de subir
    vistos = set()
    unicos = []
    for t in trabajos:
        clave = (t["source"], t["external_id"])
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(t)

    # upsert = insertar o actualizar si ya existe
    resultado = supabase.table("jobs").upsert(
        unicos,
        on_conflict="source,external_id",
    ).execute()

    print(f"💾 {len(resultado.data)} trabajos guardados/actualizados en Supabase.")


# ---------- MAIN ----------
if __name__ == "__main__":
    print("🚀 Iniciando scraping de ofertas de empleo...\n")
    todos = []
    todos.extend(scrape_remotive())
    todos.extend(scrape_remoteok())
    print(f"\n📊 Total recolectado: {len(todos)} trabajos")
    guardar_trabajos(todos)
    print("\n✅ Proceso terminado.")