"use client"
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

export default function Grupo() {
  const { cotacao_id, grupo } = useParams(); // pega os dois params da URL
  const [start, end] = grupo.split("-").map(Number); // ex: "51-100" → [51, 100]

  const offset = start - 1; // começa no índice 0
  const limit = end - start + 1; // quantidade de itens

  const { data, isLoading, error } = useQuery({
    queryKey: ["cotacao-itens", cotacao_id, offset, limit],
    queryFn: async () => {
      const res = await fetch(
        `http://servicos-coletorapi.eu8tjo.easypanel.host:8000/cotacoes/${cotacao_id}/itens?offset=${offset}&limit=${limit}`
      );
      if (!res.ok) throw new Error("Erro ao buscar itens");
      return res.json();
    },
  });

  if (isLoading) return <p>Carregando...</p>;
  if (error) return <p>Erro ao carregar itens</p>;

  return (
    <main className="flex flex-col items-center p-5 gap-5 text-white">
      <h1 className="text-lg font-bold">Itens da Cotação {cotacao_id}</h1>
      <h2>Grupo: {start}-{end}</h2>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </main>
  );
}
