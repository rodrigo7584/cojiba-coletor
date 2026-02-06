"use client";

import { useEffect, useState } from "react";
import CsvNavigator from "@/components/CsvNavigator";
import { parseCsv } from "@/utils/parseCsv";

export default function Home() {
  const [csvData, setCsvData] = useState([]);

  const loadTestCsv = async () => {
    const response = await fetch("/cods.csv");
    const text = await response.text();
    const file = new File([text], "cods.csv", { type: "text/csv" });

    parseCsv(file, (parsed) => {
      setCsvData(parsed);
      localStorage.setItem("csvData", JSON.stringify(parsed));
    });
  };

  const resetData = () => {
    setCsvData([]);
    localStorage.removeItem("csvData");
  };

  useEffect(() => {
    const saved = localStorage.getItem("csvData");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setCsvData(parsed);
      } catch (err) {
        console.error("Erro ao restaurar csvData:", err);
      }
    }
  }, []);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-6 text-center">
        Leitor de CSV com Navegação
      </h1>

      <button
        onClick={csvData.length === 0 ? loadTestCsv : resetData}
        className={`px-4 py-2 rounded mb-6 ${
          csvData.length === 0
            ? "bg-blue-500 hover:bg-blue-600"
            : "bg-red-500 hover:bg-red-600"
        } text-white`}
      >
        {csvData.length === 0 ? "Iniciar" : "Reiniciar"}
      </button>

      {csvData.length > 0 && <CsvNavigator data={csvData} />}
    </main>
  );
}
