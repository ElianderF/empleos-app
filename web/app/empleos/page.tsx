import pool from '@/lib/db'
import Link from 'next/link'
import { unstable_noStore as noStore } from 'next/cache'

const POR_PAGINA = 20

export const metadata = {
  title: 'Empleos remotos y presenciales | Bolsa de Trabajo',
  description:
    'Encuentra ofertas de empleo remoto y presencial actualizadas a diario. Filtra por modalidad, país y tecnología.',
}

type SearchParams = Promise<{
  q?: string
  modalidad?: string
  pais?: string
  tag?: string
  page?: string
}>

export default async function EmpleosPage({
  searchParams,
}: {
  searchParams: SearchParams
}) {
  noStore()

  const params = await searchParams
  const q = params.q || ''
  const modalidad = params.modalidad || ''
  const pais = params.pais || ''
  const tag = params.tag || ''
  const page = Math.max(1, parseInt(params.page || '1', 10))

  const offset = (page - 1) * POR_PAGINA

  const condiciones: string[] = ['activo = true']
  const valores: any[] = []

  if (q) {
    valores.push(`%${q}%`)
    condiciones.push(
      `(titulo ILIKE $${valores.length} OR empresa ILIKE $${valores.length})`
    )
  }
  if (modalidad) {
    valores.push(modalidad)
    condiciones.push(`modalidad = $${valores.length}`)
  }
  if (pais) {
    valores.push(`%${pais}%`)
    condiciones.push(`pais ILIKE $${valores.length}`)
  }
  if (tag) {
    valores.push(tag.toLowerCase())
    condiciones.push(`$${valores.length} = ANY(tags)`)
  }

  const where = condiciones.join(' AND ')

  const countResult = await pool.query(
    `SELECT COUNT(*)::int AS total FROM jobs WHERE ${where}`,
    valores
  )
  const total = countResult.rows[0]?.total || 0

  const dataResult = await pool.query(
    `SELECT id, titulo, empresa, modalidad, ubicacion, pais, categoria, tags,
            salario_texto, url_origen, logo_url, publicado_en
     FROM jobs
     WHERE ${where}
     ORDER BY publicado_en DESC NULLS LAST
     LIMIT $${valores.length + 1} OFFSET $${valores.length + 2}`,
    [...valores, POR_PAGINA, offset]
  )

  const jobs = dataResult.rows
  const totalPaginas = Math.ceil(total / POR_PAGINA)

  return (
    <main className="max-w-6xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold">💼 Bolsa de Trabajo</h1>
        <p className="text-gray-600 mt-1">
          Ofertas remotas y presenciales actualizadas a diario
        </p>
      </header>

      <Filtros q={q} modalidad={modalidad} pais={pais} tag={tag} />

      <p className="text-sm text-gray-500 my-4">
        {total} ofertas encontradas
      </p>

      {jobs.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No se encontraron ofertas con esos filtros.
        </div>
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {jobs.map((j: any) => (
            <li
              key={j.id}
              className="border rounded-lg p-4 hover:shadow-md transition bg-white"
            >
              <div className="flex items-start gap-3">
                {j.logo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={j.logo_url}
                    alt={j.empresa || ''}
                    className="w-10 h-10 object-contain flex-shrink-0"
                  />
                ) : null}
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-lg leading-tight">
                    {j.titulo}
                  </h3>
                  <p className="text-sm text-gray-600 mt-1 truncate">
                    {j.empresa} · {j.ubicacion || 'Sin ubicación'}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-1 mt-3">
                <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                  {j.modalidad || 'sin modalidad'}
                </span>
                {j.tags?.slice(0, 5).map((t: string) => (
                  <span
                    key={t}
                    className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
                  >
                    {t}
                  </span>
                ))}
              </div>

              {j.salario_texto ? (
                <p className="text-sm mt-2 text-green-700">
                  💰 {j.salario_texto}
                </p>
              ) : null}

              <a
                href={j.url_origen}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="inline-block mt-3 text-blue-600 font-medium hover:underline"
              >
                Ver oferta original →
              </a>
            </li>
          ))}
        </ul>
      )}

      {totalPaginas > 1 && (
        <Paginacion
          page={page}
          totalPaginas={totalPaginas}
          params={{ q, modalidad, pais, tag }}
        />
      )}
    </main>
  )
}

function Filtros({
  q,
  modalidad,
  pais,
  tag,
}: {
  q: string
  modalidad: string
  pais: string
  tag: string
}) {
  return (
    <form
      method="GET"
      action="/empleos"
      className="flex flex-wrap gap-3 p-4 bg-gray-50 rounded-lg"
    >
      <input
        name="q"
        defaultValue={q}
        placeholder="Buscar puesto o empresa..."
        className="border rounded px-3 py-2 flex-1 min-w-[200px]"
      />
      <select
        name="modalidad"
        defaultValue={modalidad}
        className="border rounded px-3 py-2"
      >
        <option value="">Toda modalidad</option>
        <option value="remoto">Remoto</option>
        <option value="presencial">Presencial</option>
        <option value="hibrido">Híbrido</option>
      </select>
      <input
        name="pais"
        defaultValue={pais}
        placeholder="País"
        className="border rounded px-3 py-2 w-40"
      />
      <input
        name="tag"
        defaultValue={tag}
        placeholder="Etiqueta (react, python...)"
        className="border rounded px-3 py-2 w-52"
      />
      <button
        type="submit"
        className="bg-blue-600 text-white px-5 py-2 rounded hover:bg-blue-700"
      >
        Filtrar
      </button>
    </form>
  )
}

function Paginacion({
  page,
  totalPaginas,
  params,
}: {
  page: number
  totalPaginas: number
  params: { q: string; modalidad: string; pais: string; tag: string }
}) {
  function url(nuevaPagina: number) {
    const p = new URLSearchParams()
    if (params.q) p.set('q', params.q)
    if (params.modalidad) p.set('modalidad', params.modalidad)
    if (params.pais) p.set('pais', params.pais)
    if (params.tag) p.set('tag', params.tag)
    p.set('page', String(nuevaPagina))
    return `/empleos?${p.toString()}`
  }

  return (
    <div className="flex justify-center items-center gap-4 mt-8">
      {page > 1 && (
        <Link
          href={url(page - 1)}
          className="px-4 py-2 border rounded hover:bg-gray-100"
        >
          ← Anterior
        </Link>
      )}
      <span className="text-sm text-gray-600">
        Página {page} de {totalPaginas}
      </span>
      {page < totalPaginas && (
        <Link
          href={url(page + 1)}
          className="px-4 py-2 border rounded hover:bg-gray-100"
        >
          Siguiente →
        </Link>
      )}
    </div>
  )
}