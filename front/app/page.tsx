"use client"
import { Button } from "@/components/ui/button";
import { CirclePlus } from "lucide-react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

type Cotacao = { 
  id: number 
  nome: string 
  status?: string
}

async function fetchCotacoes():Promise<Cotacao[]> {
  const res = await fetch("http://servicos-coletorapi.eu8tjo.easypanel.host:8000/cotacoes/")
  if(!res.ok) throw new Error("Erro ao buscar cotações")
  return res.json()
}
export default function Home() {
  const { data, isLoading, error } = useQuery<Cotacao[]>({
    queryKey:["cotacoes"],
    queryFn: fetchCotacoes,
    staleTime: 1000 * 60,
    refetchInterval: 1000 * 60
  })
  if (isLoading) return <div>Carregando...</div>
  if (error) return <div>Erro ao carregar</div>
  return (
   <div>
    <main className="flex flex-col items-center p-5 gap-5 text-white">
      <h1 className="text-lg font-bold">Cotações</h1>
        <Button asChild>
          <Link href="/criar-cotacao">
            <CirclePlus/> Criar nova cotação
          </Link>
        </Button>
        <ul>
          {data?.map((cotacao: any)=>(
            <li key={cotacao.id}>
              {cotacao.nome}
            </li>
          ))}
        </ul>
    </main>
   </div>
  );
}
