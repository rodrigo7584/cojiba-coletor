"use client"
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

export default function GerenciarCotacao() {

  async function fetchCotacao():Promise<Cotacao[]> {
    const res = await fetch("")
  }

  const { cotacao_id } = useParams(); 
  const { data, isLoading, error} = useQuery<(Cotacao[]>({
    queryKey:["cotacao"],
    queryFn: fetchCotacao,
  }))
  return (
   <div>
    <main className="flex flex-col items-center p-5 gap-5 text-white">
      <h1 className="text-lg font-bold">Gerenciar Cotação</h1>
      <h2>{cotacao_id}</h2>
    </main>
   </div>
  );
}
