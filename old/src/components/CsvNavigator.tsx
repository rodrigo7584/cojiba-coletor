"use client";

import { useEffect, useRef, useState } from "react";
import JsBarcode from "jsbarcode";

interface CsvRow {
  nome: string;
  ean: string;
  codFamilia: string;
}

export default function CsvNavigator({ data }: { data: CsvRow[] }) {
  const [index, setIndex] = useState(0);
  const [inputValue, setInputValue] = useState("");
  const barcodeRef = useRef<SVGSVGElement>(null);

  const current = data[index];
  console.log(current)
  useEffect(() => {
  if (!current?.ean || !barcodeRef.current) return;

  const { ean } = current;
  const isNumeric = /^[0-9]+$/.test(ean);
  const isValidLength = ean.length === 13 || ean.length === 8;

  if (isNumeric && isValidLength) {
    JsBarcode(barcodeRef.current, ean, {
      format: ean.length === 13 ? "EAN13" : "EAN8",
      displayValue: true,
      lineColor: "#000",
      width: 3,
      height: 100,
      valid: (isValid) => {
        if (!isValid) {
          // se checksum/fmt for inválido, limpa e avisa
          barcodeRef.current!.innerHTML = "";
          console.warn("EAN falhou na validação interna:", ean);
        }
      }
    });
  } else {
    barcodeRef.current.innerHTML = "";
    console.warn("EAN ignorado (não-numérico ou length errado):", ean);
  }
}, [current]);

  const handleGoTo = () => {
    const i = parseInt(inputValue, 10) - 1;
    if (!isNaN(i) && i >= 0 && i < data.length) {
      setIndex(i);
      setInputValue("");
    }
  };

  const goBack = () => {
    if (index > 0) setIndex(index - 1);
  };

  const goNext = () => {
    if (index < data.length - 1) setIndex(index + 1);
  };

  if (!data || data.length === 0) return <p>Nenhum dado carregado.</p>;

  return (
    <div className="flex flex-col justify-center items-center gap-6">
      <svg ref={barcodeRef}></svg>
      <div className="flex items-center h-20 text-center text-xl font-semibold">{current.nome}</div>

      <div className="flex items-center gap-4">
        <button
          onClick={goBack}
          className="bg-blue-500 text-white px-7 py-5 rounded hover:bg-blue-600"
        >
          Voltar
        </button>

        <span>
          {index + 1} / {data.length}
        </span>

        <button
          onClick={goNext}
          className="bg-blue-500 text-white px-7 py-5 rounded hover:bg-blue-600"
        >
          Avançar
        </button>
      </div>

      <div className="flex flex-col items-center gap-2">
        <input
          type="number"
          placeholder="Ir para linha..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          className="border px-7 py-5 rounded w-full"
        />
        <button
          onClick={handleGoTo}
          className="bg-blue-500 text-white px-7 py-5 rounded hover:bg-blue-600"
        >
          Ir
        </button>
      </div>
    </div>
  );
}
