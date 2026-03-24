"use client"
import { useParams } from "next/navigation";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient  } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { CircleArrowLeftIcon, FileDownIcon, ListChecksIcon, TrashIcon } from "lucide-react";
import { AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogCancel, AlertDialogAction } from "@/components/ui/alert-dialog";
import { toast } from "sonner";

type Cotacao = {
  id: string;
  nome: string;
  status: string;
  data_criacao: string;
};

export default function GerenciarCotacao() {
  const { cotacao_id } = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isPending, error } = useQuery<Cotacao>({
    queryKey: ["cotacao", cotacao_id],
    queryFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/cotacao/${cotacao_id}`);
      if (!res.ok) throw new Error("Erro ao buscar dados");
      return res.json();
    },
  });

  const finalizarMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/cotacoes/${cotacao_id}/finalizar`, {
        method: "PUT",
      });
      if (!res.ok) throw new Error("Erro ao finalizar cotação");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Cotação finalizada com sucesso!", { position: "top-center" });
      queryClient.invalidateQueries({ queryKey: ["cotacao", cotacao_id] });
    },
    onError: (error: any) => {
      toast.error(error.message || "Erro ao finalizar cotação", { position: "top-center" });
    },
  });
  const gerarMutation = useMutation({
      mutationFn: async () => {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/cotacoes/${cotacao_id}/gerar-arquivo`,
          { method: "GET" }
        );
        if (!res.ok) throw new Error("Erro ao gerar arquivo");
  
        // supondo que o backend retorna um arquivo (ex.: CSV)
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
  
        // força download
        const a = document.createElement("a");
        a.href = url;
        a.download = `cotacao-${cotacao_id}.txt`; // ou .pdf dependendo do backend
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
  
        return true;
      },
      onSuccess: () => {
        toast.success("Arquivo gerado com sucesso!", { position: "top-center" });
      },
      onError: (error: any) => {
        toast.error(error.message || "Erro ao gerar arquivo", { position: "top-center" });
      },
    });
  const deletarMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/cotacoes/${cotacao_id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Erro ao deletar cotação");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Cotação deletada com sucesso!", { position: "top-center" });
      queryClient.invalidateQueries({ queryKey: ["cotacoes"] });
      router.push("/");
    },
    onError: (error: any) => {
      toast.error(error.message || "Erro ao deletar cotação", { position: "top-center" });
    },
  });

  if (isPending) return <p className="text-white">Carregando...</p>;
  if (error) return <p className="text-red-500">Erro ao carregar cotação</p>;

  return (
    <div>
      <main className="p-5">
        <Button asChild size="icon">
          <Link href="/">
            <CircleArrowLeftIcon />
          </Link>
        </Button>

        <div className="flex flex-col items-center gap-5 text-white">
          <h1 className="text-lg font-bold">Gerenciar Cotação</h1>

          {data && (
            <div>
              <p><strong>Nome:</strong> {data.nome}</p>
              <p><strong>Status:</strong> {data.status === "F" ? "Finalizado" : "Ativa"}</p>
              <p><strong>Data criação:</strong> {new Date(data.data_criacao).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit"})}</p>
            </div>
          )}

          <div className="flex flex-row justify-center gap-2">
            {/* Botão Finalizar com popup */}
            {data?.status !== "F" && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button>
                    <ListChecksIcon /> Finalizar
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Finalizar cotação</AlertDialogTitle>
                    <AlertDialogDescription>
                      Tem certeza que deseja finalizar esta cotação?
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancelar</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() => finalizarMutation.mutate()}
                      disabled={finalizarMutation.isPending}
                    >
                      {finalizarMutation.isPending ? "Finalizando..." : "Confirmar"}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
             {data?.status === "F" && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button>
                    <TrashIcon /> Deletar
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Deletar cotação</AlertDialogTitle>
                    <AlertDialogDescription>
                      Tem certeza que deseja deletar esta cotação? Essa ação não pode ser desfeita.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancelar</AlertDialogCancel>
                    <AlertDialogAction 
                      onClick={() => deletarMutation.mutate()}
                      disabled={deletarMutation.isPending}
                    >
                      {deletarMutation.isPending ? "Deletando..." : "Confirmar"}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
            {data?.status === "F" &&(
              <Button
                onClick={() => gerarMutation.mutate()}
                disabled={gerarMutation.isPending}
              >
                <FileDownIcon/>
                {gerarMutation.isPending ? "Gerando..." : "Gerar Arquivo"}
              </Button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
