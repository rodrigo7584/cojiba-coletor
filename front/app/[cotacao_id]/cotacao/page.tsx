'use client'
import { Button } from "@/components/ui/button";
import { CircleArrowLeftIcon } from "lucide-react";
import Link from "next/dist/client/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

export default function Cotacao() {
  const { cotacao_id } = useParams();
  
  const {data, isLoading, error} = useQuery<number>({
    queryKey: ["cotacao-total-itens", cotacao_id],
    queryFn: async () => {
      const res = await fetch (`http://servicos-coletorapi.eu8tjo.easypanel.host:8000/cotacoes/${cotacao_id}/itens/total`)
      if(!res.ok) throw new Error("Erro ao buscar total de itens")
      return res.json();
    }
  })

  if (isLoading) return <p>Carregando...</p>;
  if (error) return <p>Erro ao carregar total</p>;

  const grupos = Math.ceil(data.total_itens / 50);

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
        <h2 className="text-md font-normal -mt-5">Cotação {data.total_itens}</h2>
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: grupos }, (_, i) => {
            const start = i * 50 + 1;
            const end = Math.min((i + 1) * 50, data.total_itens);
            return (
              <Button asChild key={i} className="!w-{100px}">
                <Link href={`/${cotacao_id}/cotacao/${start}-${end}`}>
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
