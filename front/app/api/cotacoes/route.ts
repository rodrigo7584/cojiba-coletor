const API = process.env.NEXT_PUBLIC_API_URL!

export async function POST(req: Request) {
  const formData = await req.formData();

  const res = await fetch(`${API}/cotacoes`, {
    method: "POST",
    body: formData,
  });

  const text = await res.text();

  return new Response(text, {
    status: res.status,
    headers: {
      "Content-Type": "application/json",
    },
  });
}