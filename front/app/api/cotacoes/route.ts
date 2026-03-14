const API = process.env.NEXT_PUBLIC_API_URL!

export async function GET() {
  const res = await fetch(`${API}/cotacoes`, { cache: "no-store" })
  const data = await res.json()

  return Response.json(data)
}

export async function POST(req: Request) {

  const formData = await req.formData()

  const res = await fetch(`${API}/cotacoes`, {
    method: "POST",
    body: formData
  })

  if (!res.ok) {
    return new Response("Erro ao criar cotação", { status: 500 })
  }

  return Response.json(await res.json())
}