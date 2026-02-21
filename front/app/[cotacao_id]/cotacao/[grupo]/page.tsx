"use client"
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card"
import {
  Carousel,
  CarouselContent,
  CarouselItem
} from "@/components/ui/carousel"
import Barcode from "react-barcode";
import { Button } from "@/components/ui/button";
import Link from "next/dist/client/link";
import { CircleArrowLeftIcon } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { redirect } from "next/navigation";

interface ItemCotacao { 
  nome_produto: string;
  familia: string; 
  ean: string; 
  preco: number; 
  promocional: string; 
}

export default function Grupo() {
  const queryClient = useQueryClient();
  const { cotacao_id, grupo } = useParams(); // pega os dois params da URL
  if (!grupo || typeof grupo !== "string") { redirect("/"); }
  const [start, end] = grupo.split("-").map(Number); // ex: "51-100" → [51, 100]
  const [precos, setPrecos] = useState<{ [familia: string]: string }>({});
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const [api, setApi] = useState<any>(null); 
  const [activeIndex, setActiveIndex] = useState(0);
  const offset = start - 1; // começa no índice 0
  const limit = end - start + 1; // quantidade de itens

// escuta o carrossel e atualiza activeIndex
  useEffect(() => {
    if (!api) return;

    const handler = () => {
      setActiveIndex(api.selectedScrollSnap());
    };

    api.on("select", handler);
    handler(); // inicializa no primeiro slide

    return () => {
      api.off("select", handler);
    };
  }, [api]);

  // foca no input quando activeIndex muda
  useEffect(() => {
    const input = inputRefs.current[activeIndex];
    if (input) {
      input.focus({ preventScroll: true });
    }
  }, [activeIndex]);
  
  const enviarPrecoMutation = useMutation({
    mutationFn: async ({ familia, preco }: { familia: string; preco: number }) => {
      const res = await fetch(
        `http://servicos-coletorapi.eu8tjo.easypanel.host:8000/cotacoes/${cotacao_id}/itens/preco?preco=${preco}&familia=${familia}`,
        { method: "PUT" }
      );
      if (!res.ok) throw new Error("Erro ao enviar preço");
      return res.json();
    },
    onSuccess: (_data, variables) => {
      // Atualiza os itens da cotação para refletir o novo preço
      queryClient.invalidateQueries({
        queryKey: ["cotacao-itens", cotacao_id, offset, limit],
      });
      setPrecos((prev) => ({ ...prev, [variables.familia]: "" }));
    },
  });

  const { data, isPending, error } = useQuery<ItemCotacao[]>({
    queryKey: ["cotacao-itens", cotacao_id, offset, limit],
    queryFn: async () => {
      const res = await fetch(
        `http://servicos-coletorapi.eu8tjo.easypanel.host:8000/cotacoes/${cotacao_id}/itens?offset=${offset}&limit=${limit}`
      );
      if (!res.ok) throw new Error("Erro ao buscar itens");
      return res.json();
    },
  });

  if (isPending) return <p>Carregando...</p>;
  if (error) return <p>Erro ao carregar itens</p>;

  return (
     <main className="p-5">
      <Button asChild size="icon">
        <Link href={`/${cotacao_id}/cotacao`}>
          <CircleArrowLeftIcon/>
        </Link>
      </Button>
      <div className="flex flex-col items-center gap-5 text-white">
        <h1 className="text-lg font-bold">Itens da Cotação {cotacao_id}</h1>
        <h2>Grupo: {start}-{end}</h2>
        <Carousel className="w-full max-w-95"  setApi={setApi}>
          <CarouselContent>
            {data?.map((item, index) => (
              <CarouselItem key={index}>
                <div className="p-1 flex flex-col justify-center">
                  <Card>
                    <CardContent className="flex flex-col items-center justify-center p-2 w-full h-62">
                      <span className="text-xs font-semibold text-center">{item.nome_produto.split(":")[0]}</span>
                      <span className="text-xs font-semibold text-center">{item.nome_produto.split(":")[1]}</span>
                      <span>{item.ean}</span>
                      <span>{item.familia}</span>
                      <span>{item.preco}</span>
                      <span className="text-xs">tamanho ean:{item.ean.length}</span>
                      {item.ean.length === 13 ? (
                        <Barcode value={item.ean} format="EAN13" width={4}/>
                      ) : item.ean.length === 8 ? (
                        <Barcode value={item.ean} format="EAN8"  width={4}/>
                      ) : (
                        <h1>EAN inválido</h1>
                      )}
                    </CardContent>
                  </Card>
                  <Input
                    type="text"
                    inputMode="numeric"
                    ref={(el) => { inputRefs.current[index] = el; }}
                    value={precos[item.familia] || ""}
                    onChange={(e) => {
                      let val = e.target.value.replace(/\D/g, ""); // só números
                      if (val === "") {
                        setPrecos((prev) => ({ ...prev, [item.familia]: "" }));
                        return;
                      }

                      // transforma em centavos
                      let num = parseInt(val, 10);

                      // divide por 100 para colocar o ponto
                      let formatted = (num / 100).toFixed(2);

                      setPrecos((prev) => ({ ...prev, [item.familia]: formatted }));
                    }}
                    onKeyDown={(e) => { 
                      if (e.key === "Enter") { 
                        enviarPrecoMutation.mutate({ 
                          familia: item.familia, preco: parseFloat(precos[item.familia]), }); 
                        } 
                      }}
                    className="w-full p-2 rounded mt-2 font-bold"
                  />


                  <Button
                    className="mt-2"
                    onClick={() =>
                      enviarPrecoMutation.mutate({
                        familia: item.familia,
                        preco: parseFloat(precos[item.familia]),
                      })
                    }
                    disabled={enviarPrecoMutation.isPending}
                  >
                    {enviarPrecoMutation.isPending ? "Enviando..." : "Enviar"}
                  </Button>

                </div>
              </CarouselItem>
            ))}
          </CarouselContent>
          {/* <CarouselPrevious />
          <CarouselNext /> */}
        </Carousel>
      </div>
    </main>
  );
}
