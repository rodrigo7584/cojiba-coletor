'use client'
import { Button } from "@/components/ui/button";
import { CircleArrowLeftIcon } from "lucide-react";
import Link from "next/dist/client/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

type CotacaoDetalhes = {
  id: string;
  nome: string;
  status: string;
};

export default function Cotacao() {
  const { cotacao_id } = useParams();

  // Query 1: total de itens
  const { data: totalData, isPending: loadingTotal, error: errorTotal } = useQuery<{ total_itens: number }>({
    queryKey: ["cotacao-total-itens", cotacao_id],
    queryFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/cotacoes/${cotacao_id}/itens/total`);
      if (!res.ok) throw new Error("Erro ao buscar total de itens");
      return res.json();
    }
  });

  // Query 2: detalhes da cotação
  const { data: detalhesData, isPending: loadingDetalhes, error: errorDetalhes } = useQuery<CotacaoDetalhes>({
    queryKey: ["cotacao-detalhes", cotacao_id],
    queryFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/cotacao/${cotacao_id}`);
      if (!res.ok) throw new Error("Erro ao buscar detalhes da cotação");
      return res.json();
    }
  });

  if (loadingTotal || loadingDetalhes) return <p>Carregando...</p>;
  if (errorTotal || errorDetalhes) return <p>Erro ao carregar dados</p>;

  const grupos = Math.ceil(totalData.total_itens / 50);

  return (
    <div>
      <main className="p-5">
        <Button asChild size="icon">
          <Link href="/">
            <CircleArrowLeftIcon />
          </Link>
        </Button>

        <div className="flex flex-col items-center gap-5 text-white">
          <h1 className="text-lg font-bold">Cotação {cotacao_id}</h1>
          <h2 className="text-md font-normal -mt-5">
            {detalhesData?.nome} ({detalhesData?.status})
          </h2>
          <h3>Total de itens: {totalData.total_itens}</h3>

          <div className="flex flex-wrap justify-center gap-2">
            {Array.from({ length: grupos }, (_, i) => {
              const start = i * 50 + 1;
              const end = Math.min((i + 1) * 50, totalData.total_itens);
              return (
                <Button asChild key={i} className="w-25">
                  <Link href={`/${cotacao_id}/cotacao/${start}-${end}`} >
                    {start}-{end}
                  </Link>
                </Button>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}
