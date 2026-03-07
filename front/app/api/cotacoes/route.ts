const API = process.env.NEXT_PUBLIC_API_URL!

export async function GET() {
  const res = await fetch(`${API}/cotacoes`, {
    cache: "no-store"
  })

  if (!res.ok) {
    return new Response("Erro ao buscar cotações", { status: 500 })
  }

  const data = await res.json()

  return Response.json(data)
}