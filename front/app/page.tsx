"use client"
import { Button } from "@/components/ui/button";
import { CirclePlus, FileCogIcon, FileUpIcon } from "lucide-react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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
    <main className="flex flex-col items-center jus p-5 gap-5 text-white">
      <h1 className="text-lg font-bold">Cotações</h1>
        <Button asChild>
          <Link href="/criar-cotacao">
            <CirclePlus/> Criar nova cotação
          </Link>
        </Button>
        <Table className="w-100">
          <TableCaption>Lista de cotações</TableCaption>
          <TableHeader>
            <TableRow className="text-white">
              <TableHead className="w-25">Nome</TableHead>
              <TableHead className="w-25 text-center">Criação</TableHead>
              <TableHead className="w-25 text-center">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
              {data?.map((cotacao: any)=>(
              <TableRow key={cotacao.id}>
                <TableCell className="w-25">{cotacao.nome}</TableCell>
                <TableCell className="w-25 text-center">{new Date(cotacao.data_criacao).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit"})}</TableCell>
                <TableCell className="flex flex-row justify-center gap-2">
                  {cotacao?.status === "F" && (
                  <Button asChild>
                    <Link href={`/${cotacao.id}/gerenciar-cotacao`}>
                      <FileCogIcon/> Gerenciar
                    </Link>
                  </Button>
                  )}
                  {cotacao?.status === "A" && (
                  <Button asChild>
                    <Link href={`/${cotacao.id}/cotacao`}>
                      <FileUpIcon/> Cotar
                    </Link>
                  </Button>
                  )}
                </TableCell>
              </TableRow>
              ))}            
          </TableBody>
        </Table>
    </main>
   </div>
  );
}
