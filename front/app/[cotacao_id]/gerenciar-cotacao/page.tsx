"use client"
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

type Cotacao = {
  id: string;
  nome: string;
  status: string;
  data: string;
};

export default function GerenciarCotacao() {
  const { cotacao_id } = useParams();

  const { data, isLoading, error } = useQuery<Cotacao>({
    queryKey: ["cotacao", cotacao_id],
    queryFn: async () => {
      const res = await fetch(
        `http://servicos-coletorapi.eu8tjo.easypanel.host:8000/cotacao/${cotacao_id}`
      );
      if (!res.ok) throw new Error("Erro ao buscar dados");
      return res.json();
    },
  });
  console.log(data)
  if (isLoading) {
    return <p className="text-white">Carregando...</p>;
  }

  if (error) {
    return <p className="text-red-500">Erro ao carregar cotação</p>;
  }

  return (
    <div>
      <main className="flex flex-col items-center p-5 gap-5 text-white">
        <h1 className="text-lg font-bold">Gerenciar Cotação</h1>
        <h2>ID: {cotacao_id}</h2>

        {data && (
          <div className="mt-4">
            <p><strong>Nome:</strong> {data[0].nome}</p>
            {/* Renderize outros campos da cotação aqui */}
          </div>
        )}
      </main>
    </div>
  );
}
