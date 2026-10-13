"use client"
import { toast } from "sonner"
import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CircleArrowLeftIcon, CirclePlus, CircleQuestionMarkIcon, FileSpreadsheetIcon } from "lucide-react";
import Link from "next/link";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogFooter, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";


export default function Criar() {
  const [fileName, setFileName] = useState<string | null>(null);
  const [nomeCotacao, setNomeCotacao] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);

  const mutation = useMutation<any,Error,{arquivo: File; nome: string}>({
    mutationFn: async ({ arquivo, nome }) => {
      const formData = new FormData();
      formData.append("arquivo", arquivo); // campo esperado no FastAPI
      formData.append("nome", nome);       // campo esperado no FastAPI

      const response = await fetch("/api/cotacoes", {
        method: "POST",
        body: formData,
      });

      let data;

      try {
        data = await response.json();
      } catch {
        data = null;
      }

      if (!response.ok) {
        throw new Error(data?.detail || "Erro ao criar cotação");
      }

      return data;
    },
    onSuccess: (data) => {
      console.log("Cotação criada:", data);
      toast.success("Cotação criada com sucesso!", { position: "top-center" })
      setNomeCotacao("")
      setFileName(null)
      if (inputRef.current) { 
        inputRef.current.value = ""; 
      }
    },
    onError: (error) => {
      console.error(error);
      toast.error(error.message, { position: "top-center" })
    },
  });

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setFileName(file.name);
    } else {
      setFileName(null);
    }
  };

  const handleButtonClick = () => {
    if (inputRef.current) {
      inputRef.current.click();
    }
  };

  const handleSubmit = () => {
    if (!inputRef.current || !inputRef.current.files?.[0] || !nomeCotacao) {
      alert("Selecione um arquivo CSV e digite um nome");
      return;
    }
    mutation.mutate({
      arquivo: inputRef.current.files[0],
      nome: nomeCotacao,
    });
  };

  return (
    <div>
      <main className="p-5">
        <Button asChild size="icon">
          <Link href="/">
            <CircleArrowLeftIcon/>
          </Link>
        </Button>
        <div className="flex flex-col items-center p-5 gap-5 text-white">
          <div className="flex gap-1 items-center justify-center">
            <h1 className="text-lg font-bold">Criar cotação</h1>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button>
                  <CircleQuestionMarkIcon />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogTitle>Tutorial de geração do arquivo CSV</AlertDialogTitle>
                <p>
                  O relátorio gerado em análise abc de venda varejo com os filtros de produto e familia. 
                </p>
                <p>
                  Selecione as colunas: <br/>
                  <span className="font-semibold">Código Produto</span> <br/>
                  <span className="font-semibold">Produto : Família</span> <br/>
                  <span className="font-semibold">Código Família</span> <br/>
                  <span className="font-semibold">Embalagem Unitária</span> <br/> 
                  e salve em um arquivo CSV,
                  geralmente é copiado uma linha com um <span className="font-semibold">valor total</span>, essa linha tem de ser deletada. 
                 </p>
                <AlertDialogFooter>
                  <AlertDialogCancel>Fechar</AlertDialogCancel>
                </AlertDialogFooter>
              </AlertDialogContent>
              
            </AlertDialog>
          </div>
          <Input
            placeholder="Digite o nome para a cotação"
            className="w-60"
            maxLength={30}
            value={nomeCotacao} // vem do useState
            onChange={(e) => setNomeCotacao(e.target.value)}
          />
          <Input
            type="file"
            accept=".csv"
            ref={inputRef}
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
          <Button onClick={handleButtonClick} className="w-50">
            <FileSpreadsheetIcon />
            {fileName ? fileName : "Selecione um CSV"}
          </Button>
          <Button className="w-50" onClick={handleSubmit} disabled={mutation.isPending}>
            <CirclePlus /> {mutation.isPending ? "Enviando..." : "Criar nova cotação"}
          </Button>
        </div>
      </main>
    </div>
  );
}
