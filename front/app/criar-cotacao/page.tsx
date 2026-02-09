"use client"
import { toast } from "sonner"
import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CircleArrowLeftIcon, CirclePlus, FileSpreadsheetIcon } from "lucide-react";
import Link from "next/link";

export default function Criar() {
  const [fileName, setFileName] = useState(null);
  const [nomeCotacao, setNomeCotacao] = useState("");
  const inputRef = useRef(null);

  const mutation = useMutation({
    mutationFn: async ({ arquivo, nome }) => {
      const formData = new FormData();
      formData.append("arquivo", arquivo); // campo esperado no FastAPI
      formData.append("nome", nome);       // campo esperado no FastAPI

      const response = await fetch("http://servicos-coletorapi.eu8tjo.easypanel.host:8000/cotacoes/", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Erro ao criar cotação");
      }
      return response.json();
    },
    onSuccess: (data) => {
      console.log("Cotação criada:", data);
      toast.success("Cotação criada com sucesso!", { position: "top-center" })
      setNomeCotacao("")
      setFileName(null)
      inputRef.current.value = null
    },
    onError: (error) => {
      console.error(error);
      toast.error(error.message || "Erro ao criar cotação", { position: "top-center" })
    },
  });

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setFileName(file.name);
    } else {
      setFileName(null);
    }
  };

  const handleButtonClick = () => {
    inputRef.current.click();
  };

  const handleSubmit = () => {
    if (!inputRef.current.files[0] || !nomeCotacao) {
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
          <h1 className="text-lg font-bold">Criar cotação</h1>
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
          <Button className="w-50" onClick={handleSubmit} disabled={mutation.isLoading}>
            <CirclePlus /> {mutation.isLoading ? "Enviando..." : "Criar nova cotação"}
          </Button>
        </div>
      </main>
    </div>
  );
}
